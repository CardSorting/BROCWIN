// Content-validated startup resources and engine-scoped compiled Wasm modules.
// Storage failures are cache misses. Guest state and mutable settings never persist.
(function(root) {
  'use strict';
  const digest = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)),
    b => b.toString(16).padStart(2, '0')).join('');
  const policies = Object.freeze({
    'balanced-v1': Object.freeze({id:'balanced-v1', maxBytes:128*1024*1024, maxEntry:16*1024*1024, preload:8}),
    'conservative-v1': Object.freeze({id:'conservative-v1', maxBytes:64*1024*1024, maxEntry:8*1024*1024, preload:4})
  });
  function policy(environment, override) {
    if (override && !policies[override]) throw new Error('Unknown runtime cache policy');
    return policies[override || (environment.deviceMemory >= 8 && environment.hardwareConcurrency >= 4
      ? 'balanced-v1' : 'conservative-v1')];
  }
  function database() {
    return new Promise((resolve,reject) => {
      const request = indexedDB.open('brocwin-runtime-cache-v2',1);
      request.onupgradeneeded = () => {
        request.result.createObjectStore('bytes',{keyPath:'key'});
        request.result.createObjectStore('modules',{keyPath:'key'});
        request.result.createObjectStore('metadata',{keyPath:'key'});
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
      request.onblocked = () => reject(new Error('Runtime cache database blocked'));
    });
  }
  const requestValue = request => new Promise((resolve,reject) => {
    request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error);
  });
  const complete = transaction => new Promise((resolve,reject) => {
    transaction.oncomplete = resolve; transaction.onerror = transaction.onabort = () => reject(transaction.error);
  });
  class Cache {
    constructor(configuration, identity, db) {
      this.policy=configuration; this.identity=identity; this.db=db;
      this.inflight=new Map(); this.writeChain=Promise.resolve();
      this.stats={byteHits:0,byteMisses:0,downloadBytes:0,avoidedBytes:0,moduleHits:0,moduleMisses:0,
        invalid:0,storageFailures:0,policy:configuration.id};
    }
    async get(store,key) {
      if (!this.db) return undefined;
      try { return await requestValue(this.db.transaction(store).objectStore(store).get(key)); }
      catch (_) {this.stats.storageFailures++; return undefined;}
    }
    async remove(store,key) {
      if (!this.db) return;
      try {const tx=this.db.transaction(store,'readwrite');tx.objectStore(store).delete(key);await complete(tx);}
      catch (_) {this.stats.storageFailures++;}
    }
    put(store,row) {
      // Serialize eviction and insert so concurrent downloads cannot exceed the budget.
      this.writeChain=this.writeChain.then(async()=>{
        if (!this.db) return;
        const tx=this.db.transaction([store,'metadata'],'readwrite'), objects=tx.objectStore(store);
        const metadata=tx.objectStore('metadata');
        const done=complete(tx), all=(await requestValue(metadata.getAll())).filter(r=>r.store===store);
        const max=store==='bytes'?this.policy.maxBytes:4;
        let used=all.filter(r=>r.key!==row.key).reduce((n,r)=>n+(store==='bytes'?r.size:1),0);
        for(const old of all.filter(r=>r.key!==row.key).sort((a,b)=>a.key<b.key?-1:a.key>b.key?1:0)) {
          if(used+(store==='bytes'?row.size:1)<=max)break;
          objects.delete(old.key);metadata.delete(old.key);used-=store==='bytes'?old.size:1;
        }
        try { objects.put(row);metadata.put({key:row.key,store,size:row.size||1});await done; }
        catch(error) {try{tx.abort();}catch(_){} await done.catch(()=>{});throw error;}
      }).catch(()=>{this.stats.storageFailures++;});
      return this.writeChain;
    }
    async bytes(url,hash) {
      if(!/^[a-f0-9]{64}$/.test(hash))throw new Error('Resource cache needs a SHA-256 identity');
      const key=this.identity+':'+hash;
      if(this.inflight.has(key))return (await this.inflight.get(key)).slice();
      const operation=(async()=>{
        const row=await this.get('bytes',key);
        if(row?.bytes instanceof ArrayBuffer && row.size===row.bytes.byteLength && await digest(row.bytes)===hash) {
          this.stats.byteHits++;this.stats.avoidedBytes+=row.size;return new Uint8Array(row.bytes);
        }
        if(row){this.stats.invalid++;await this.remove('bytes',key);}
        this.stats.byteMisses++;
        const response=await (this.fetchOriginal || fetch)(url);
        if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);
        const bytes=new Uint8Array(await response.arrayBuffer());
        if(await digest(bytes)!==hash)throw new Error(`Input changed since prepare: ${url}`);
        this.stats.downloadBytes+=bytes.byteLength;
        if(bytes.byteLength<=this.policy.maxEntry)
          await this.put('bytes',{key,size:bytes.byteLength,bytes:bytes.slice().buffer});
        return bytes;
      })();
      this.inflight.set(key,operation);
      try {return (await operation).slice();} finally {this.inflight.delete(key);}
    }
    async module(url,hash) {
      const key=this.identity+':'+hash+':'+navigator.userAgent;
      const bytes=await this.bytes(url,hash);
      const row=await this.get('modules',key);
      if(row?.hash===hash && row.module instanceof WebAssembly.Module) {
        this.stats.moduleHits++;return row.module;
      }
      if(row){this.stats.invalid++;await this.remove('modules',key);}
      this.stats.moduleMisses++;
      const capabilityKey='engine:'+navigator.userAgent;
      const capability=await this.get('modules',capabilityKey);
      let module;
      if(capability?.cloneSupported===false && WebAssembly.compileStreaming) {
        const address=new URL(url,location.href);address.searchParams.set('sha256',hash);
        const response=await (this.fetchOriginal || fetch)(address.href);
        if(!response.ok)throw new Error(`${url}: HTTP ${response.status}`);
        const validation=response.clone().arrayBuffer().then(async value=>{
          if(await digest(value)!==hash)throw new Error(`Input changed since prepare: ${url}`);
        });
        [module]=await Promise.all([WebAssembly.compileStreaming(response),validation]);
        this.stats.moduleMode='engine-streaming-cache';
      } else {
        module=await WebAssembly.compile(bytes);
        const failures=this.stats.storageFailures;
        await this.put('modules',{key,hash,module});
        if(this.db && this.stats.storageFailures!==failures) {
          await this.put('modules',{key:capabilityKey,cloneSupported:false});
          this.stats.moduleMode='validated-bytes';
        } else this.stats.moduleMode=this.db?'indexeddb-module':'validated-bytes';
      }
      return module;
    }
    installResourceFetch(manifest) {
      const files=new Map(manifest.files.filter(f=>f.loadMode==='required' &&
        /\.(dll|ttf|ttc|otf|fon)$/i.test(f.url) && f.size<=this.policy.maxEntry)
        .map(f=>[new URL(f.url,location.href).href,f]));
      const original=window.fetch;
      const self=this;
      // Cache.bytes uses the original fetch to avoid recursive interception.
      this.fetchOriginal=original;
      window.fetch=function(input,options){
        // Only bare string GETs are eligible. Preserve all explicit transport
        // options and non-string inputs (including cross-realm Requests).
        if(typeof input!=='string' || options!==undefined)return original.apply(this,arguments);
        let url;
        try {url=new URL(input,location.href);} catch(_){return original.apply(this,arguments);}
        const file=files.get(url.href);
        if(!file)return original.apply(this,arguments);
        return self.resourceBytes(url.href,file.sha256).then(bytes=>new Response(bytes,
          {status:200,headers:{'Content-Length':String(bytes.byteLength),'Content-Type':'application/octet-stream'}}));
      };
    }
    async resourceBytes(url,hash) {
      // Preserve global interception for unrelated requests while this cache's
      // internal download uses the captured transport directly.
      return this.bytes(url,hash);
    }
  }
  async function open(manifest, override) {
    const selected=policy(navigator,override);
    const identity=await digest(new TextEncoder().encode(JSON.stringify({
      schema:1,commit:manifest.runtime.commit,wasm:manifest.runtime.wasm.sha256,
      scripts:manifest.runtime.scripts,integration:manifest.runtime.integration})));
    let db;
    try {db=await database();} catch(_){db=null;}
    return new Cache(selected,identity,db);
  }
  root.BrocwinRuntimeCache={open,policy,digest,Cache};
  if(typeof module!=='undefined')module.exports=root.BrocwinRuntimeCache;
})(typeof globalThis!=='undefined'?globalThis:this);
