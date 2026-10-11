"""Check real WebGL queue presentation, including the shipped render worker.

Uses the existing loopback browser server and the same browser as capture.py.
No original client is launched by this renderer contract regression.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/python'))
from playwright.sync_api import sync_playwright

SCRIPT = r"""async () => {
  const same=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(label+': '+JSON.stringify(a));};
  const rgba=surface=>{const c=document.createElement('canvas');c.width=c.height=8;
    const ctx=c.getContext('2d');ctx.drawImage(surface,0,0);return [...ctx.getImageData(1,1,1,1).data];};
  const pixel=frame=>[...frame.pixels.slice(0,4)];
  const resources=[{id:501,width:8,height:8,format:22},{id:502,width:8,height:8,format:22}];
  const results=[];
  for(const version of [1,2]) {
    const c=document.createElement('canvas');c.width=c.height=8;
    const d=new D3D9Backend.Device(c,{webglVersion:version});
    try {
      resources.forEach(r=>d.createColor(r));
      d.clear([1,0,0,1],1);
      d.clear([0,1,0,1],1,1,null,null,0,resources[0]);
      d.clear([0,0,1,1],1,1,null,null,0,resources[1]);
      same(rgba(d.present(resources)),[255,0,0,255],'first displayed frame');
      same(pixel(d.readColor(null)),[0,255,0,255],'next implicit image');
      same(pixel(d.readColor(resources[0])),[255,0,0,255],'remaining queued image');
      same(rgba(d.present(resources)),[0,255,0,255],'second displayed frame');
      same(pixel(d.readColor(null)),[255,0,0,255],'third image reaches index zero');
      same(rgba(d.present()),[0,0,255,255],'single-buffer COPY frame');
      same(pixel(d.readColor(null)),[255,0,0,255],'COPY retains pixels');
      if(d.gpu.getError())throw Error('GL error');
      results.push({backend:'webgl'+version,route:'direct',status:'passed'});
    } finally {d.destroy();}
  }
  const module=await WebAssembly.compile(await (await fetch('/build/wine-assembly.wasm')).arrayBuffer());
  const sigs=(await (await fetch('/lib/host-import-sigs.generated.json')).json()).sigs;
  const memory=new WebAssembly.Memory({initial:8192,maximum:8192,shared:true}),host={memory};
  for(const [name,sig]of Object.entries(sigs))host[name]=sig.results?.length?()=>0:()=>{};
  const e=(await WebAssembly.instantiate(module,{host})).exports;e.d3dim_worker_init(0x400000);
  const manager=new RenderWorker.Manager({module,memory,sigs,imageBase:0x400000,sourceVersion:'theseus-swapchain-regression',
    workerFactory:()=>new Worker('/lib/d3d-render-worker.js'),reclaimHeap:head=>e.d3d_render_adopt_free_list(head)});
  const bitmaps=[];
  try {
    await manager.ready;
    const port=manager.createEndpoint({api:'neutral',backend:'webgl'});await port.ready;
    const consumer=new D3DCommandStream.WorkerConsumer(port);
    const queue=new D3DCommandStream.CommandQueue({deviceId:7,generation:1,consumer});
    const OP=D3DCommandStream.OPCODES;
    const issue=async(opcode,payload={})=>{const r=queue.submit(opcode,payload);await queue.fence(r.sequence,r.generation);return await r.value;};
    await issue(OP.RESOURCE_CREATE,{kind:'device',backend:'webgl',width:8,height:8});
    for(const resource of resources)await issue(OP.RESOURCE_CREATE,{kind:'color',resource});
    await issue(OP.CLEAR,{color:[1,0,0,1],flags:1});
    await issue(OP.CLEAR,{color:[0,1,0,1],flags:1,depthAttachment:null,colorAttachment:resources[0]});
    await issue(OP.CLEAR,{color:[0,0,1,1],flags:1,depthAttachment:null,colorAttachment:resources[1]});
    const first=await issue(OP.PRESENT,{backbuffers:resources});bitmaps.push(first.bitmap);
    same(rgba(first.bitmap),[255,0,0,255],'worker first frame');
    same(pixel(await issue(OP.READBACK)),[0,255,0,255],'worker next implicit image');
    same(pixel(await issue(OP.READBACK,{resource:resources[0]})),[255,0,0,255],'worker remaining queue');
    const second=await issue(OP.PRESENT,{backbuffers:resources});bitmaps.push(second.bitmap);
    same(rgba(second.bitmap),[0,255,0,255],'worker second frame');
    same(rgba(first.bitmap),[255,0,0,255],'published bitmap is immutable');
    await issue(OP.RESOURCE_UPDATE,{kind:'reset',width:8,height:8,depthAttachment:null});
    await issue(OP.CLEAR,{color:[1,0,1,1],flags:1});
    const reset=await issue(OP.PRESENT,{backbuffers:[]});bitmaps.push(reset.bitmap);
    same(rgba(reset.bitmap),[255,0,255,255],'reset retires queue');
    await issue(OP.RESOURCE_RELEASE,{kind:'device'});await port.terminate();
    results.push({backend:'webgl',route:'shared-render-worker',status:'passed'});
  } finally {bitmaps.forEach(b=>b?.close());await manager.stop();}
  return results;
}"""

if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            page.route('**/__swapchain_test', lambda route: route.fulfill(status=200,
                       headers={'Content-Type': 'text/html', 'Cross-Origin-Opener-Policy': 'same-origin',
                                'Cross-Origin-Embedder-Policy': 'require-corp'},
                       body='<!doctype html><title>Direct3D presentation regression</title>'))
            page.goto('http://127.0.0.1:8766/__swapchain_test')
            for name in ['region-map.generated', 'render-worker', 'd3d-command-stream',
                         'gpu-backend', 'd3d9-shader', 'd3d9-fixed', 'd3d9-backend']:
                page.add_script_tag(url='/lib/' + name + '.js')
            results = page.evaluate(SCRIPT)
            print(json.dumps({'test': 'WebGL backbuffer queue', 'browser': browser.version,
                              'wasmSha256': hashlib.sha256((HERE.parent / 'tools/wine-assembly/build/wine-assembly.wasm').read_bytes()).hexdigest(),
                              'results': results}))
        finally:
            browser.close()
