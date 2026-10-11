// Bounded compatibility-boundary telemetry. No guest memory or gameplay probes.
(() => {
  const now = () => performance.now();
  const data = window.brocwinTelemetry = {schema: 'brocwin.startup-telemetry/v1',
    marks: {}, fetches: [], wasm: [], shaders: [], frames: [], longTasks: [], api: [],
    totals: {frameSamples: 0, longTasks: 0, longTaskDurationMs: 0},
    retainedWindow: {frames: 'Latest 2048 observed frame changes', longTasks: 'Latest 2048 tasks'}};
  const retain = (rows, value) => {rows.push(value);if(rows.length>2048)rows.shift();};
  performance.setResourceTimingBufferSize(12000);
  const fetchOriginal = window.fetch;
  window.fetch = async function(input, options) {
    const start = now();
    const url = new URL(typeof input === 'string' ? input : input.url, location.href);
    const row = {path: url.pathname, start, range: options?.headers?.Range || null};
    try { const result = await fetchOriginal.apply(this, arguments);
      row.headersAt = now(); row.status = result.status; return result;
    } finally { if (data.fetches.length < 12000) data.fetches.push(row); }
  };
  for (const name of ['compile', 'instantiate', 'compileStreaming', 'instantiateStreaming']) {
    const original = WebAssembly[name];
    WebAssembly[name] = async function() {
      const start = now();
      try { return await original.apply(this, arguments); }
      finally { if (data.wasm.length < 128) data.wasm.push({name, start, end: now()}); }
    };
  }
  for (const type of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
    if (!type) continue;
    for (const name of ['compileShader', 'linkProgram']) {
      const original = type.prototype[name];
      type.prototype[name] = function() {
        const start = now();
        try { return original.apply(this, arguments); }
        finally { if (data.shaders.length < 2048) data.shaders.push({name, start, end: now()}); }
      };
    }
  }
  try { new PerformanceObserver(list => {
    for (const entry of list.getEntries()) {
      data.totals.longTasks++;
      data.totals.longTaskDurationMs += entry.duration;
      retain(data.longTasks, {start: entry.startTime, duration: entry.duration});
    }
  }).observe({entryTypes: ['longtask']}); } catch (_) {}
  let lastFrame = 0;
  const poll = setInterval(() => {
    const t = window.theseus;
    if (!t) return;
    if (!data.marks[t.state]) data.marks[t.state] = now();
    if (t.frames !== lastFrame) {
      const r=t.client?.renderer;
      data.totals.frameSamples++;
      retain(data.frames, {at: now(), total: t.frames || 0, gpu: t.frameKinds?.gpu || 0,
        lastComposite:r?._workerLastCompositeAt,publicationDepth:r?._workerGuestSliceDepth,
        windows:Object.values(r?.windows||{}).map(w=>({width:w.w,height:w.h,visible:w.visible,
          gpuWidth:w._dxFrameLayer?.canvas?.width,gpuHeight:w._dxFrameLayer?.canvas?.height}))});
      lastFrame = t.frames;
    }
    if (t.frameKinds?.gpu && !data.marks.firstGPU) data.marks.firstGPU = now();
  }, 100);
  data.finish = () => { clearInterval(poll);
    data.resources = performance.getEntriesByType('resource').slice(0, 12000).map(e =>
      ({path: new URL(e.name).pathname, start: e.startTime, duration: e.duration,
        transfer: e.transferSize, encoded: e.encodedBodySize, decoded: e.decodedBodySize}));
    data.api = window.theseus?.client?.guestWorker?.broker?.stats()?.calls || [];
    return data;
  };
})();
