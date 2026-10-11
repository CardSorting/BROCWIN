"""Real-browser persistence, invalidation, corruption and uncached fallback."""
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from prepare import HERE, ROOT
from serve import Handler
sys.path.insert(0, str(ROOT / 'theseus/tools/python'))
from playwright.sync_api import sync_playwright


class RuntimeCacheTest(unittest.TestCase):
    def test_validated_persistence_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp, sync_playwright() as p:
            folder=Path(temp)
            wasm=bytes.fromhex('0061736d01000000')
            (folder/'empty.wasm').write_bytes(wasm)
            (folder/'index.html').write_text('<script src="runtime_cache.js"></script><script src="artifact.js"></script><script src="texture.js"></script><script src="shader.js"></script>')
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
            server.paths={'/':folder/'index.html','/runtime_cache.js':HERE/'runtime_cache.js','/empty.wasm':folder/'empty.wasm',
                '/input.dll':folder/'empty.wasm'}
            library=ROOT/'theseus/tools/wine-assembly/lib'
            server.paths.update({'/artifact.js':library/'validated-artifact-cache.js',
                '/texture.js':library/'d3d9-texture.js','/shader.js':library/'d3d9-shader.js'})
            threading.Thread(target=server.serve_forever,daemon=True).start()
            digest=hashlib.sha256(wasm).hexdigest()
            config={'runtime':{'commit':'test','wasm':{'sha256':digest},'scripts':[], 'integration':{}},'files':[]}
            rows=[]
            try:
                for ordinal in range(2):
                    context=p.chromium.launch_persistent_context(str(folder/'profile'),channel='msedge',headless=True)
                    page=context.pages[0]
                    page.goto(f'http://127.0.0.1:{server.server_port}/')
                    row=page.evaluate('''async ({config,hash,ordinal})=>{
                      const cache=await BrocwinRuntimeCache.open(config,'balanced-v1');
                      if(BrocwinRuntimeCache.policy({deviceMemory:4,hardwareConcurrency:4}).id!=='conservative-v1'
                          || BrocwinRuntimeCache.policy({deviceMemory:8,hardwareConcurrency:4}).id!=='balanced-v1'
                          || BrocwinRuntimeCache.policy({},'balanced-v1').id!=='balanced-v1')throw Error('Policy selection not replayable');
                      let badPolicy=false;try{BrocwinRuntimeCache.policy({},'unknown');}catch(_){badPolicy=true;}
                      if(!badPolicy)throw Error('Unvalidated policy accepted');
                      const a=await cache.module('/empty.wasm',hash);
                      if (!(a instanceof WebAssembly.Module)) throw Error('Missing module');
                      const artifacts=await ValidatedArtifactCache.open('persistent-test');
                      artifacts.install(D3D9Shader,D3D9Texture);
                      const words=Uint32Array.from([0xfffe0101,1,0xc00f0000,0x90e40000,65535]);
                      const output=D3D9Shader.compile(words);
                      const pixels=D3D9Texture.decode(new Uint8Array([0,248,0,0,0,0,0,0]),4,4,D3D9Texture.DXT1);
                      if(pixels[0]!==255||pixels[1]!==0||!output.source.includes('gl_Position'))throw Error('Wrong artifact');
                      await artifacts.pending;
                      cache.installResourceFetch({files:[{url:'/input.dll',loadMode:'required',size:8,sha256:hash}]});
                      const before=cache.stats.byteHits;
                      const abort=new AbortController();abort.abort();
                      for(const call of [()=>fetch(new Request(new URL('/input.dll',location.href),{signal:abort.signal})),
                          ()=>fetch('/input.dll',{signal:abort.signal})]) {
                        let cancelled=false;try{await call();}catch(error){cancelled=error.name==='AbortError';}
                        if(!cancelled)throw Error('Cache swallowed resource cancellation');
                      }
                      if(cache.stats.byteHits!==before)throw Error('Cancelled resource entered cache');
                      const range=await fetch('/input.dll',{headers:{Range:'bytes=0-3'}});
                      if(range.status!==206 || (await range.arrayBuffer()).byteLength!==4)throw Error('Range transport changed');
                      const request=await fetch(new Request(new URL('/input.dll',location.href)));
                      if(!request.url.endsWith('/input.dll'))throw Error('Request transport metadata changed');
                      const eligible=await fetch('/input.dll');
                      if((await eligible.arrayBuffer()).byteLength!==8 || cache.stats.byteHits!==before+1)
                        throw Error('Eligible bare resource did not reuse validated bytes');
                      if(ordinal===1 && artifacts.stats.hits!==2)throw Error('Artifacts did not persist');
                      if(ordinal===1){
                        if(!cache.stats.byteHits)throw Error('No persisted resource hit');
                        const key=cache.identity+':'+hash;
                        await cache.put('bytes',{key,size:8,bytes:new ArrayBuffer(8)});
                        await cache.bytes('/empty.wasm',hash);
                        if(cache.stats.invalid!==1)throw Error('Corrupt bytes accepted');
                        const changed=structuredClone(config);changed.runtime.commit='changed';
                        const other=await BrocwinRuntimeCache.open(changed,'balanced-v1');
                        await other.bytes('/empty.wasm',hash);
                        if(other.stats.byteHits!==0)throw Error('Runtime identity not invalidated');
                        let rejected=false;try{await cache.bytes('/empty.wasm','f'.repeat(64));}catch(_){rejected=true;}
                        if(!rejected)throw Error('Invalid source digest accepted');
                        const fallback=new BrocwinRuntimeCache.Cache(cache.policy,'no-db',null);
                        await fallback.module('/empty.wasm',hash);
                        if(fallback.stats.moduleMisses!==1)throw Error('Fallback did not compile');
                        const tx=artifacts.db.transaction('artifacts','readwrite'),store=tx.objectStore('artifacts');
                        const done=new Promise((resolve,reject)=>{tx.oncomplete=resolve;tx.onerror=reject;});
                        const rows=await new Promise((resolve,reject)=>{const q=store.getAll();q.onsuccess=()=>resolve(q.result);q.onerror=reject;});
                        const shader=rows.find(r=>r.input.startsWith('shader:'));
                        shader.result.source='corrupt';store.put(shader);await done;
                        const recovered=await ValidatedArtifactCache.open('persistent-test');
                        if(recovered.stats.invalid!==1)throw Error('Corrupt shader accepted');
                        const invalidated=await ValidatedArtifactCache.open('new-version');
                        if(invalidated.entries.size!==0)throw Error('Compiler version not invalidated');
                      }
                      return {resources:cache.stats,artifacts:artifacts.stats};
                    }''',{'config':config,'hash':digest,'ordinal':ordinal})
                    rows.append(row)
                    context.close()
                print(json.dumps({'realBrowserCache':rows}))
            finally:
                server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
