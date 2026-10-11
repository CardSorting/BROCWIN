'use strict';

// The existing Winsock frame wire, carried over a browser WebSocket. The
// original client still produces and consumes every game-protocol byte.
class TheseusLocalServerWire {
  constructor(configuration, onChange = () => {}) {
    const url = new URL(configuration.webSocketUrl);
    if (url.protocol !== 'ws:' || url.hostname !== '127.0.0.1' || url.pathname !== '/vln' ||
        url.username || url.password || url.search || url.hash) throw new Error('Invalid local transport URL');
    this.inbox = [];
    this.queuedBytes = 0;
    this.state = 'connecting';
    this.closeInfo = null;
    this.localCloseReason = null;
    this.socketError = false;
    this.onChange = onChange;
    this.udpPorts = new Set(configuration.udpPorts || []);
    if (configuration.clientIp && configuration.clientIp !== '10.0.0.1') throw new Error('Invalid virtual client address');
    this.clientIp = 0x0a000001;
    this.udpMappings = new Map(); // Native ephemeral port -> this session's virtual source port.
    this.stats = {sentFrames: 0, receivedFrames: 0, sentBytes: 0, receivedBytes: 0,
      sentTypes: {}, receivedTypes: {}, unsupportedDatagrams: 0, locallyDeliveredDatagrams: 0,
      mappedSelfDatagrams: 0};
    // Bounded endpoint metadata only: no game payload or widened routing.
    this.datagramRoutes = [];
    this.untrackedDatagramAttempts = 0;
    this.socket = new WebSocket(url, 'theseus-vln1');
    this.socket.binaryType = 'arraybuffer';
    this.ready = new Promise((resolve, reject) => {
      let opened = false;
      const timer = setTimeout(() => { this.close('connect-timeout'); reject(new Error('Local transport timed out')); }, 10000);
      this.socket.addEventListener('open', () => {
        clearTimeout(timer);
        opened = true;
        this.state = 'open';
        onChange(this.state);
        resolve();
      }, {once: true});
      this.socket.addEventListener('close', event => {
        clearTimeout(timer);
        this.closeInfo = {at: new Date().toISOString(), code: event.code ?? null,
          reason: event.reason ?? '', wasClean: event.wasClean ?? null};
        if (!opened) reject(new Error('Local transport connection failed'));
        this.disconnected();
      }, {once: true});
      this.socket.addEventListener('error', () => {
        clearTimeout(timer);
        this.socketError = true;
        reject(new Error('Local transport failed'));
      }, {once: true});
    });
    this.socket.addEventListener('message', event => {
      const bytes = new Uint8Array(event.data);
      if (bytes.length < 28 || bytes.length > 65535) return this.close('invalid-frame-extent');
      const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
      const kind = view.getUint32(4, true);
      if (view.getUint32(0, true) !== 0x314e4c56 ||
          view.getUint32(24, true) !== bytes.length - 28 || ![2, 3, 4, 5, 6, 8, 9].includes(kind) ||
          (kind !== 6 && bytes.length > 4124)) return this.close('invalid-frame-header');
      if (kind === 9) {
        const guestPort = view.getUint32(12, true), nativePort = view.getUint32(20, true);
        if (bytes.length !== 28 || view.getUint32(8, true) !== this.clientIp ||
            view.getUint32(16, true) !== this.clientIp || guestPort < 1 || guestPort > 65535 ||
            nativePort < 1 || nativePort > 65535 ||
            (this.udpMappings.has(nativePort) && this.udpMappings.get(nativePort) !== guestPort) ||
            (!this.udpMappings.has(nativePort) && this.udpMappings.size >= 128)) return this.close('invalid-udp-mapping');
        this.udpMappings.set(nativePort, guestPort);
        return; // Transport metadata is not a Winsock frame or game packet.
      }
      this.stats.receivedFrames++;
      this.stats.receivedBytes += bytes.length;
      this.stats.receivedTypes[kind] = (this.stats.receivedTypes[kind] || 0) + 1;
      if (this.inbox.length >= 40000 || this.queuedBytes + bytes.length > 8 * 1024 * 1024) return this.close('receive-queue-capacity');
      this.inbox.push(bytes);
      this.queuedBytes += bytes.length;
      this.onDeliver?.();
    });
  }

  disconnected() {
    if (this.state === 'closed') return;
    this.state = 'closed';
    this.udpMappings.clear();
    // Host GONE (-1 peer) is the existing Winsock transport-loss contract.
    const gone = new Uint8Array(28), view = new DataView(gone.buffer);
    [0x314e4c56, 7, 0xffffffff, 0, 0xffffffff, 0, 0].forEach((v, i) => view.setUint32(i * 4, v, true));
    this.inbox = [gone];
    this.queuedBytes = gone.length;
    this.onChange(this.state);
    this.onDeliver?.();
  }

  send(bytes) {
    if (bytes.length < 28) return false;
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const kind = view.getUint32(4, true);
    let localDatagram = false, mappedSelf = false;
    if (kind === 6) {
      const [sourceIp, sourcePort, destinationIp, destinationPort] = [8, 12, 16, 20].map(p => view.getUint32(p, true));
      mappedSelf = sourceIp === this.clientIp && destinationIp === this.clientIp &&
        this.udpMappings.get(destinationPort) === sourcePort;
      localDatagram = destinationIp === this.clientIp && !mappedSelf;
      const supported = localDatagram || mappedSelf || destinationIp === 0x7f000001 && this.udpPorts.has(destinationPort);
      if (!supported) this.stats.unsupportedDatagrams++;
      let route = this.datagramRoutes.find(r => r.sourceIp === sourceIp && r.sourcePort === sourcePort &&
        r.destinationIp === destinationIp && r.destinationPort === destinationPort);
      if (!route && this.datagramRoutes.length < 32) {
        route = {sourceIp, sourcePort, destinationIp, destinationPort, supported, attempts: 0, payloadBytes: 0};
        this.datagramRoutes.push(route);
      }
      if (route) { route.attempts++; route.payloadBytes += bytes.length - 28; }
      else this.untrackedDatagramAttempts++;
    }
    if (localDatagram) {
      // The original client sends UDP to its own bound virtual socket during
      // field entry. Reflect those exact bytes into the same Winsock receive
      // path; they must never be sent to a native or external destination.
      if (bytes.length > 65535 || this.inbox.length >= 40000 || this.queuedBytes + bytes.length > 8 * 1024 * 1024) return false;
      const frame = bytes.slice(); // The Wasm send scratch is immediately reused.
      this.inbox.push(frame); this.queuedBytes += frame.length;
      this.stats.locallyDeliveredDatagrams++;
      this.onDeliver?.();
      return true;
    }
    if (this.state === 'closed') {
      // A new connection after transport loss must fail, not wait forever.
      if (kind === 1) {
        if (this.inbox.length >= 40000) return false;
        const reset = bytes.slice(0, 28), r = new DataView(reset.buffer);
        r.setUint32(4, 5, true);
        r.setUint32(8, view.getUint32(16, true), true);
        r.setUint32(12, view.getUint32(20, true), true);
        r.setUint32(16, view.getUint32(8, true), true);
        r.setUint32(20, view.getUint32(12, true), true);
        r.setUint32(24, 0, true);
        this.inbox.push(reset);
        this.queuedBytes += reset.length;
        this.onDeliver?.();
      }
      return true;
    }
    if (this.socket.readyState !== WebSocket.OPEN || this.socket.bufferedAmount + bytes.length > 1024 * 1024) return false;
    this.socket.send(bytes);
    if (mappedSelf) this.stats.mappedSelfDatagrams++;
    this.stats.sentFrames++;
    this.stats.sentBytes += bytes.length;
    this.stats.sentTypes[kind] = (this.stats.sentTypes[kind] || 0) + 1;
    return true;
  }

  peek() { return this.inbox[0] || null; }
  commit() { const frame = this.inbox.shift(); if (frame) this.queuedBytes -= frame.length; }
  close(reason = 'requested') {
    if (this.state !== 'closed' && this.localCloseReason === null) this.localCloseReason = reason;
    this.socket.close(); this.disconnected();
  }
  snapshot() { return {state: this.state, ...this.stats, queuedFrames: this.inbox.length, queuedBytes: this.queuedBytes,
    closeInfo: this.closeInfo && {...this.closeInfo}, localCloseReason: this.localCloseReason, socketError: this.socketError,
    datagramRoutes: this.datagramRoutes.map(route => ({...route})), untrackedDatagramAttempts: this.untrackedDatagramAttempts,
    udpMappings: [...this.udpMappings].map(([nativePort, guestPort]) => ({nativePort, guestPort}))}; }
}

if (typeof module !== 'undefined') module.exports = {TheseusLocalServerWire};
