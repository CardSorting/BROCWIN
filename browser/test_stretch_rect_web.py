"""Compare native StretchRect pixels with WebGL 1/2 and the shipped render worker."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/python'))
from playwright.sync_api import sync_playwright

SCRIPT = r"""async native => {
  const OP=D3DCommandStream.OPCODES,results=[];
  const check=(yes,message)=>{if(!yes)throw Error(message);};
  const bytes=words=>new Uint8Array(new Uint32Array(words).buffer);
  async function cases(issue){
    let id=100,count=0,maxDifference=0;
    for(const row of native.cases){
      if(row.hr)continue;
      const make=async spec=>{
        if(spec.kind==='backbuffer')return null;
        const resource={id:++id,width:spec.width,height:spec.height,format:spec.format};
        await issue(OP.RESOURCE_CREATE,{kind:'color',resource});return resource;
      };
      const source=await make(row.source),destination=await make(row.destination);
      try{
        await issue(OP.RESOURCE_UPDATE,{kind:'color',resource:source,pixels:bytes(row.input),pitch:row.source.width*4});
        await issue(OP.RESOURCE_UPDATE,{kind:'color',resource:destination,pixels:bytes(row.before),pitch:row.destination.width*4});
        const rect=r=>r?{x:r[0],y:r[1],width:r[2]-r[0],height:r[3]-r[1]}:null;
        await issue(OP.COPY,{kind:'color',source,destination,sourceRect:rect(row.sourceRect),destinationRect:rect(row.destinationRect),filter:row.filter});
        const frame=await issue(OP.READBACK,{resource:destination}),expected=bytes(row.pixels);
        check(frame.pixels.length===expected.length,row.name+' dimensions');
        for(let i=0;i<expected.length;i++){
          if(i%4===3&&row.destination.format===22)continue; // X8 is unspecified.
          const difference=Math.abs(frame.pixels[i]-expected[i]);maxDifference=Math.max(maxDifference,difference);
          check(difference<=(row.filter===2?1:0),row.name+' byte '+i+': '+frame.pixels[i]+' / '+expected[i]);
        }
        count++;
      }finally{await issue(OP.RESOURCE_RELEASE,{kind:'color-set',ids:[source?.id,destination?.id].filter(Boolean)});}
    }
    // The source has just been rendered into; the destination was sampled and
    // cached. The transfer must preserve source data and invalidate that cache.
    const a={id:9001,width:2,height:2,format:21},b={id:9002,width:2,height:2,format:21};
    for(const resource of[a,b])await issue(OP.RESOURCE_CREATE,{kind:'color',resource});
    const draw=D3D9ColorAliasCases.draw({...D3D9ColorAliasCases.level(b),sampler:{addressU:3,addressV:3,min:1,mag:1,mip:0}});
    const vertices=new Float32Array(draw.vertices.buffer);vertices[8]=63;vertices[17]=63;
    await issue(OP.DRAW,draw);
    for(const color of[[1,0,0,1],[0,1,1,.5]]){
      await issue(OP.CLEAR,{color,flags:1,depthAttachment:null,colorAttachment:a});
      await issue(OP.COPY,{kind:'color',source:a,destination:b,filter:2});
      await issue(OP.DRAW,draw);
      const frame=await issue(OP.READBACK,{}),expected=[color[2],color[1],color[0],color[3]].map(v=>Math.round(v*255));
      check(frame.pixels.every((v,i)=>Math.abs(v-expected[i%4])<=1),'copy invalidates sampled render target');
    }
    // Copy into a target whose explicit draw variant is currently bound. A
    // later rebind/read must not write the old variant over the transfer.
    await issue(OP.CLEAR,{color:[0,0,0,1],flags:1,depthAttachment:null,colorAttachment:b});
    await issue(OP.COPY,{kind:'color',source:a,destination:b,filter:0});
    const held=await issue(OP.READBACK,{resource:b});
    check(held.pixels.every((v,i)=>Math.abs(v-[255,255,0,128][i%4])<=1),'copy into bound target survives variant save');
    await issue(OP.RESOURCE_RELEASE,{kind:'color-set',ids:[a.id,b.id]});
    return {cases:count,maxChannelDifference:maxDifference,renderedSourceAndCache:true};
  }
  for(const version of[1,2]){
    const canvas=document.createElement('canvas');canvas.width=canvas.height=16;
    const device=new D3D9Backend.Device(canvas,{webglVersion:version});
    const issue=async(op,p)=>{
      if(op===OP.RESOURCE_CREATE)return device.createColor(p.resource);
      if(op===OP.RESOURCE_UPDATE)return device.updateColor(p.resource,p.pixels,p.pitch);
      if(op===OP.RESOURCE_RELEASE){p.ids.forEach(id=>device.releaseColor(id));return 1;}
      if(op===OP.READBACK)return device.readColor(p.resource);
      if(op===OP.CLEAR)return device.clear(p.color,p.flags,1,null,p.depthAttachment,0,p.colorAttachment);
      if(op===OP.DRAW)return device.draw(p);
      if(op===OP.COPY){
        const gl=device.gpu.gl,read=gl.readPixels;gl.readPixels=()=>{throw Error('WebGL copy attempted CPU readback');};
        try{return device.copyColor(p);}finally{gl.readPixels=read;}
      }
      throw Error('unknown test operation');
    };
    try{device.clear([0,0,0,1],1);results.push({route:'webgl'+version+'-direct',...await cases(issue)});
      check(device.gpu.getError()===0,'GL error');}finally{device.destroy();}
  }
  const module=await WebAssembly.compile(await(await fetch('/build/wine-assembly.wasm')).arrayBuffer());
  const sigs=(await(await fetch('/lib/host-import-sigs.generated.json')).json()).sigs;
  const memory=new WebAssembly.Memory({initial:8192,maximum:8192,shared:true}),host={memory};
  for(const[name,sig]of Object.entries(sigs))host[name]=sig.results?.length?()=>0:()=>{};
  const e=(await WebAssembly.instantiate(module,{host})).exports;e.d3dim_worker_init(0x400000);
  const manager=new RenderWorker.Manager({module,memory,sigs,imageBase:0x400000,sourceVersion:'theseus-stretch-regression',
    workerFactory:()=>new Worker('/lib/d3d-render-worker.js'),reclaimHeap:head=>e.d3d_render_adopt_free_list(head)});
  try{
    await manager.ready;const port=manager.createEndpoint({api:'neutral',backend:'webgl'});await port.ready;
    const consumer=new D3DCommandStream.WorkerConsumer(port),queue=new D3DCommandStream.CommandQueue({deviceId:7,generation:1,consumer});
    const issue=async(op,p={})=>{const r=queue.submit(op,p);await queue.fence(r.sequence,r.generation);const v=await r.value;if(v?.error)throw Error(v.error);return v;};
    await issue(OP.RESOURCE_CREATE,{kind:'device',backend:'webgl',width:16,height:16});
    results.push({route:'webgl-shared-render-worker',...await cases(issue)});
    await issue(OP.RESOURCE_RELEASE,{kind:'device'});await port.terminate();
  }finally{await manager.stop();}
  return results;
}"""

if __name__ == '__main__':
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            page.route('**/__stretch_test', lambda route: route.fulfill(status=200,
                       headers={'Content-Type': 'text/html', 'Cross-Origin-Opener-Policy': 'same-origin',
                                'Cross-Origin-Embedder-Policy': 'require-corp'},
                       body='<!doctype html><title>StretchRect regression</title>'))
            page.goto('http://127.0.0.1:8766/__stretch_test')
            for name in ['region-map.generated', 'render-worker', 'd3d-command-stream',
                         'gpu-backend', 'd3d9-shader', 'd3d9-fixed', 'd3d9-blit', 'd3d9-backend']:
                page.add_script_tag(url='/lib/' + name + '.js')
            page.add_script_tag(path=str(HERE.parent / 'tools/wine-assembly/test/fixtures/d3d9-color-alias-cases.js'))
            reference = json.loads((HERE / 'reference/stretch-rect.json').read_text())
            results = page.evaluate(SCRIPT, reference)
            print(json.dumps({'test': 'native StretchRect with WebGL', 'browser': browser.version,
                              'wasmSha256': hashlib.sha256((HERE.parent / 'tools/wine-assembly/build/wine-assembly.wasm').read_bytes()).hexdigest(),
                              'results': results}))
        finally:
            browser.close()
