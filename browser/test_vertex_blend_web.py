"""Replay actual WAT/Bridge DRAW snapshots through WebGL1/2 against D3D9."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'theseus/tools/python'))
from playwright.sync_api import sync_playwright

DRAW=r'''({capture,reference})=>{
  const revive=v=>v&&typeof v==='object'?(v.$type?new globalThis[v.$type](v.data):
    Array.isArray(v)?v.map(revive):Object.fromEntries(Object.entries(v).map(([k,x])=>[k,revive(x)]))):v;
  const out=[];
  for(const version of [1,2]){
    const canvas=document.createElement('canvas');canvas.width=canvas.height=reference.size;
    const device=new D3D9Backend.Device(canvas,{webglVersion:version});
    try{
      for(let i=0;i<capture.draws.length;i++){
        const draw=revive(capture.draws[i]);device.clear([16/255,32/255,48/255,1],1);device.draw(draw);
        const bytes=device.readColor(null).pixels,rgba=bytes.slice();
        for(let j=0;j<bytes.length;j+=4){rgba[j]=bytes[j+2];rgba[j+2]=bytes[j];}
        out.push({version,index:i,rgba:Array.from(rgba),error:device.gpu.getError()});
      }
    }finally{device.destroy();}
  }
  return out;
}'''

def main():
    import base64
    ref=json.loads((HERE/'reference/fixed-vertex-blending.json').read_text())
    capture_path=Path(sys.argv[1])
    capture=json.loads(capture_path.read_text())
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        try:
            page=browser.new_page()
            for name in ['gpu-backend','d3d-shader-ir','d3d9-shader','d3d9-fixed','d3d9-backend']:
                page.add_script_tag(path=str(ROOT/'theseus/tools/wine-assembly/lib'/f'{name}.js'))
            result=page.evaluate(DRAW,{'capture':capture,'reference':ref})
        finally:browser.close()
    bg=bytes([16,32,48,255]);size=ref['size'];results=[]
    for row in result:
        actual=bytes(row.pop('rgba'))
        reference_index=capture['results'][row['index']].get('referenceIndex',row['index'])
        want=base64.b64decode(ref['cases'][reference_index]['rgba'])
        mismatch=sum((actual[i:i+4]==bg)!=(want[i:i+4]==bg) for i in range(0,len(want),4))
        error=0;interior=0
        for y in range(1,size-1):
            for x in range(1,size-1):
                at=(y*size+x)*4
                if any(want[((y+dy)*size+x+dx)*4:((y+dy)*size+x+dx)*4+4]==bg
                       for dy in [-1,0,1] for dx in [-1,0,1]):continue
                interior+=1;error=max(error,max(abs(a-b) for a,b in zip(actual[at:at+4],want[at:at+4])))
        row.update(coverageMismatch=mismatch,interiorMax=error,interiorPixels=interior)
        results.append(row);print(json.dumps(row))
    capture_path.with_name('fixed-blend-webgl.json').write_text(json.dumps(results,indent=2)+'\n')
    assert all(r['error']==0 and r['interiorPixels']>20 and r['interiorMax']<=2 and r['coverageMismatch']<=3 for r in results)
    print(f'PASS {len(results)} WebGL1/2 fixed-blend draws from actual WAT device calls against native D3D9 pixels')

if __name__=='__main__':main()
