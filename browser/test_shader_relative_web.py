"""Exercise production relative-constant uploads; optionally compare captured skinning shaders.

Captured transform feedback uses original IR/vertices/constants but omits textures
and rasterization. It is a shader differential, not a gameplay or scene replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / 'tools/wine-assembly/lib'
sys.path.insert(0, str(HERE.parent / 'tools/python'))
from playwright.sync_api import sync_playwright

CHECK = r"""() => {
  const rows=[];
  const bits=n=>new Uint32Array(new Float32Array([n]).buffer)[0];
  const color=(n,local=false)=>[n/255,local?.75:.25,local?.5:.125,1];
  for(const version of [1,2]) {
    const canvas=document.createElement('canvas'); canvas.width=canvas.height=8;
    const device=new D3D9Backend.Device(canvas,{webglVersion:version});
    try {
      for(const defs of [[],[0,2,63,95],Array.from({length:96},(_,i)=>i)]) {
        // c50 appears before the relative read, exercising nonnumeric Map order.
        const instructions=[1,0xc00f0000,0x90e40000,1,0x800f0000,0xa0e40032,
          1,0xb0010000,0x90000001,1,0xd00f0000,0xa0e42000,
          1,0xd0020000,0x80550000];
        for(const n of defs)instructions.push(81,0xa00f0000|n,...color(n,true).map(bits));
        const vs=Uint32Array.from([0xfffe0101,...instructions,65535]);
        const constants=new Float32Array(96*4);
        for(let n=0;n<96;n++)constants.set(color(n),n*4);
        for(const address of [-1,0,.75,1,2,3,49,50,62,63,64,94,95,96]) {
          for(const update of [false,true]) {
            // Same program must observe subsequent API constant changes.
            constants[50*4+1]=update?.625:.25;
            const draw={primitive:4,primitiveCount:1,stride:16,
              vertices:new Uint8Array(new Float32Array([-1,-1,.5,address,3,-1,.5,address,-1,3,.5,address]).buffer),
              attributes:[{register:0,usage:0,usageIndex:0,type:2,offset:0},
                {register:1,usage:5,usageIndex:0,type:0,offset:12}],
              vertexShader:vs,pixelShader:Uint32Array.from([0xffff0101,1,0x800f0000,0x90e40000,65535]),
              vertexConstants:constants,pixelConstants:new Float32Array(32),textures:[],
              state:{zenable:false,zwrite:false,cull:1}};
            device.clear([.1,.1,.1,.1],1);device.draw(draw);
            const p=device.readColor(null).pixels.slice((4*8+4)*4,(4*8+5)*4);
            const actual=[p[2],p[1],p[0],p[3]],n=Math.floor(address);
            const expected=n>=0&&n<96?color(n,defs.includes(n)):[0,0,0,0];
            expected[1]=defs.includes(50)?.75:(update?.625:.25);
            const rgba=expected.map(x=>Math.round(255*x));
            if(actual.some((v,i)=>Math.abs(v-rgba[i])>1))throw Error(JSON.stringify({version,defs:defs.length,address,update,actual,rgba}));
            rows.push({version,definitions:defs.length,address,update,actual,expected:rgba});
          }
        }
      }
    } finally {device.destroy();}
  }
  return rows;
}"""

EDGES = r"""() => {
  const rows=[],bits=x=>new Uint32Array(new Float32Array([x]).buffer)[0];
  for(const version of [1,2])for(const bank of [96,256]) {
    const canvas=document.createElement('canvas');canvas.width=canvas.height=4;
    const gpu=new GpuBackend.WebGLBackend(canvas,{apiVersion:version,alpha:true}),gl=gpu.gl;
    const instructions=[{opcode:1,args:[0xc00f0000,0x90e40000]},
      {opcode:bank===96?1:46,args:[0xb0010000,0x90000001]},
      {opcode:1,args:[0xd00f0000,0xa0e42000]},
      {opcode:81,args:[0xa00f0002,...[.5,.75,.25,1].map(bits)]}];
    const lowered=D3D9Shader.compileIR({stage:'vertex',version:bank===96?0xfffe0101:0xfffe0200,
      instructions:instructions.map((x,i)=>({...x,offset:i+1}))},{experimentalVS20:bank===256});
    // Call the exact generated helper with raw float addresses. Real MOV/MOVA
    // rounds first; these checks protect helper bounds and conversion guards.
    const vs=lowered.source.split('void main()')[0]+
      'void main(){gl_Position=d3d_v0;d3d_color0=d3d_relative(d3d_v1.x);}';
    const p=gpu.createProgram(vs,'precision highp float;varying vec4 d3d_color0;void main(){gl_FragColor=d3d_color0;}',
      lowered.attributes,lowered.uniforms);
    for(const [name,n]of Object.entries(lowered.relativeFloatUniforms))gpu.setUniform(p,name,'4f',[n/255,.25,.125,1]);
    const input=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,input);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,0,1,3,-1,0,1,-1,3,0,1]),gl.STATIC_DRAW);
    const pos=p.attributes.d3d_v0;gl.enableVertexAttribArray(pos);gl.vertexAttribPointer(pos,4,gl.FLOAT,false,0,0);
    gl.disableVertexAttribArray(p.attributes.d3d_v1);gpu.useProgram(p);
    for(const address of [-Infinity,-1,-0,0,.5,1,2,3,bank-1,bank,Infinity,NaN]) {
      gl.vertexAttrib4f(p.attributes.d3d_v1,address,0,0,0);gl.drawArrays(gl.TRIANGLES,0,3);
      const actual=new Uint8Array(4);gl.readPixels(1,1,1,1,gl.RGBA,gl.UNSIGNED_BYTE,actual);
      const value=Number.isInteger(address)&&address>=0&&address<bank
        ?address===2?[.5,.75,.25,1]:[address/255,.25,.125,1]:[0,0,0,0];
      const expected=value.map(x=>Math.round(x*255));
      if(gl.getError()||actual.some((x,i)=>Math.abs(x-expected[i])>1))throw Error(JSON.stringify({version,bank,address:String(address),actual:[...actual],expected}));
      rows.push({version,bank,address:String(address),actual:[...actual],expected});
    }
    gl.deleteBuffer(input);gpu.destroy();gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
  const canvas=document.createElement('canvas');canvas.width=canvas.height=16;
  const device=new D3D9Backend.Device(canvas,{webglVersion:2});
  try {
    for(const fillMode of [1,2])for(const address of [3,63]) {
      const constants=new Float32Array(96*4);constants.set([.25,.5,.75,1],address*4);
      const position=[1,0xc00f0000,0x90e40000];
      const relative=Uint32Array.from([0xfffe0101,...position,1,0xb0010000,0x90000001,
        1,0xd00f0000,0xa0e42000,65535]);
      const direct=Uint32Array.from([0xfffe0101,...position,1,0xd00f0000,0xa0e40000|address,65535]);
      const draw={primitive:4,primitiveCount:1,stride:16,
        vertices:new Uint8Array(new Float32Array([-.75,-.75,.5,address,.75,-.75,.5,address,-.75,.75,.5,address]).buffer),
        attributes:[{register:0,usage:0,usageIndex:0,type:2,offset:0},{register:1,usage:5,usageIndex:0,type:0,offset:12}],
        pixelShader:Uint32Array.from([0xffff0101,1,0x800f0000,0x90e40000,65535]),
        vertexConstants:constants,textures:[],state:{fillMode,zenable:false,zwrite:false,cull:1}};
      const outputs=[];
      for(const vertexShader of [direct,relative]){
        device.clear([0,0,0,0],1);device.draw({...draw,vertexShader});outputs.push(device.readColor(null).pixels.slice());
      }
      if(!outputs[0].some(x=>x)||outputs[0].some((x,i)=>x!==outputs[1][i]))throw Error('outline constant upload mismatch');
      rows.push({version:2,fillMode,address,bitExact:true,nonzeroBytes:outputs[0].filter(x=>x).length});
    }
  } finally {device.destroy();}
  return rows;
}"""

FEEDBACK = r"""({payload,control}) => {
  const revive=x=>{
    if(!x||typeof x!=='object')return x;
    if(x.base64!==undefined){
      if(x.capturedBytes!==x.byteLength)throw Error('truncated binary payload');
      const b=Uint8Array.from(atob(x.base64),c=>c.charCodeAt(0));
      return new globalThis[x.type](b.buffer);
    }
    if(Array.isArray(x))return x.map(revive);
    return Object.fromEntries(Object.entries(x).map(([k,v])=>[k,revive(v)]));
  };
  const draw=revive(payload),bytes=draw.vertexShader.nativeBytes;
  const ir=D3DShaderIR.read(bytes.buffer,bytes.byteOffset);
  const translator=control?controlShader:D3D9Shader;
  const canvas=document.createElement('canvas');canvas.width=canvas.height=16;
  const gpu=new GpuBackend.WebGLBackend(canvas,{apiVersion:2}),gl=gpu.gl;
  const t0=performance.now(),shader=translator.compileIR(ir),t1=performance.now();
  // Capture every original vertex output, including clip position. This adds
  // feedback declarations only; all recovered shader instructions are intact.
  const outputs=[...shader.source.matchAll(/varying vec4 (\w+);/g)].map(m=>m[1]);
  const names=['capturedPosition',...outputs];
  const source='varying vec4 capturedPosition;\n'+shader.source.replace(/}\s*$/,'capturedPosition=gl_Position;\n}');
  const p=gpu.createProgram(source,'precision highp float;void main(){gl_FragColor=vec4(1.0);}',
    shader.attributes,shader.uniforms,{transformFeedbackVaryings:names});
  const t2=performance.now();
  for(const name of shader.uniforms){
    const index=shader.relativeFloatUniforms?.[name]??Number(name.match(/^d3d_vs_c(\d+)$/)?.[1]);
    if(!Number.isInteger(index))throw Error('unexpected captured uniform '+name);
    gpu.setUniform(p,name,'4f',draw.vertexConstants.subarray(index*4,index*4+4));
  }
  const input=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,input);gl.bufferData(gl.ARRAY_BUFFER,draw.vertices,gl.STATIC_DRAW);
  for(const a of draw.attributes){
    const location=gl.getAttribLocation(p.handle,'d3d_v'+a.register);if(location<0)continue;
    const size=[1,2,3,4,4][a.type];if(!size)throw Error('unsupported captured attribute');
    gl.enableVertexAttribArray(location);gl.vertexAttribPointer(location,size,a.type===4?gl.UNSIGNED_BYTE:gl.FLOAT,a.type===4,draw.stride,a.offset);
  }
  const count=draw.vertices.byteLength/draw.stride;
  if(!Number.isInteger(count))throw Error('incomplete captured vertices');
  const output=gl.createBuffer(),feedback=gl.createTransformFeedback();
  gl.bindTransformFeedback(gl.TRANSFORM_FEEDBACK,feedback);
  gl.bindBuffer(gl.TRANSFORM_FEEDBACK_BUFFER,output);
  gl.bufferData(gl.TRANSFORM_FEEDBACK_BUFFER,count*names.length*16,gl.STREAM_READ);
  gl.bindBufferBase(gl.TRANSFORM_FEEDBACK_BUFFER,0,output);gpu.useProgram(p);
  gl.enable(gl.RASTERIZER_DISCARD);gl.beginTransformFeedback(gl.POINTS);
  gl.drawArrays(gl.POINTS,0,count);gl.endTransformFeedback();
  const values=new Float32Array(count*names.length*4);
  gl.getBufferSubData(gl.TRANSFORM_FEEDBACK_BUFFER,0,values);gl.finish();
  const t3=performance.now(),error=gl.getError();
  const ext=gl.getExtension('WEBGL_debug_renderer_info');
  const renderer=ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  if(error)throw Error('feedback GL error '+error);
  const words=new Uint32Array(values.buffer);
  const result={control,vertices:count,outputs:names,sourceBytes:source.length,
    translationMs:t1-t0,compileLinkMs:t2-t1,uploadAndFirstExecutionMs:t3-t2,totalMs:t3-t0,
    renderer,words:Array.from(words),finiteValues:Array.from(values).filter(Number.isFinite).length};
  gl.deleteTransformFeedback(feedback);gl.deleteBuffer(input);gl.deleteBuffer(output);
  gl.getExtension('WEBGL_lose_context')?.loseContext();return result;
}"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--control', type=Path)
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = {'scope': 'Production upload pixels plus optional original-shader transform differential',
              'sourceHashes': {n: hashlib.sha256((LIB / n).read_bytes()).hexdigest()
                               for n in ['d3d9-shader.js', 'd3d9-backend.js']}}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        report['browserVersion'] = browser.version
        try:
            page = browser.new_page()
            if args.control:
                page.add_script_tag(path=str(args.control.resolve()))
                page.evaluate('window.controlShader=window.D3D9Shader')
                report['controlHash'] = hashlib.sha256(args.control.read_bytes()).hexdigest()
            for name in ['gpu-backend', 'd3d-shader-ir', 'd3d9-shader', 'd3d9-fixed', 'd3d9-backend']:
                page.add_script_tag(path=str(LIB / (name + '.js')))
            report['pixels'] = page.evaluate(CHECK)
            print(f"PASS {len(report['pixels'])} production WebGL1/2 relative/static/DEF/update pixel cases", flush=True)
            report['edges'] = page.evaluate(EDGES)
            print(f"PASS {len(report['edges'])} helper edge and production outline cases", flush=True)
            report['capturedShaders'] = []
            if args.capture:
                assert args.control, '--capture requires an explicit preserved --control'
                selected = []
                for filename in ['character-preview-render-state.json', 'first-world-render-state.json']:
                    data = json.loads((args.capture / filename).read_text())
                    for device in data['devices']:
                        for command in device['pendingCommands']:
                            payload = command.get('payload', {})
                            if command['sequence'] in [79554, 109872, 109877]:
                                selected.append((command['sequence'], payload))
                assert len(selected) == 3
                for sequence, payload in selected:
                    results = []
                    for control in [True, False]:
                        print(f'Measuring original draw {sequence}: ' + ('control' if control else 'array'), flush=True)
                        result = page.evaluate(FEEDBACK, {'payload': payload, 'control': control})
                        results.append(result)
                        print(json.dumps({k: v for k, v in result.items() if k != 'words'}), flush=True)
                    before, after = results
                    assert before['outputs'] == after['outputs']
                    assert before['words'] == after['words'], f'Original shader outputs differ: {sequence}'
                    for result in results:
                        words = result.pop('words')
                        result['outputWordCount'] = len(words)
                        result['outputSha256'] = hashlib.sha256(json.dumps(words).encode()).hexdigest()
                    report['capturedShaders'].append({'sequence': sequence, 'bitExact': True, 'results': results})
                    if args.output:
                        args.output.write_text(json.dumps(report, indent=2) + '\n')
            report['limitations'] = [
                'Texture data was omitted from captured payloads; this does not replay full scene pixels.',
                'Same browser/driver, sequential control then candidate; driver caches are uncontrolled.',
                'Transform feedback changes program linkage; integrated original-game replay is separately required.']
        finally:
            browser.close()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('PASS relative uniform verification', flush=True)


if __name__ == '__main__':
    main()
