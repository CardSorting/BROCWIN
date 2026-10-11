"""Compare the integrated WebGL backend with native diffuse-color linkage."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'tools/python'))
from playwright.sync_api import sync_playwright

DRAW = r"""({cases, captured}) => {
  const results = [];
  const fixed = {lighting: false, specular: false, fog: false, textureFactor: 0xbf4080ff,
    stages: [{colorOp: 2, colorArg1: 3, colorArg2: 1, alphaOp: 2, alphaArg1: 3, alphaArg2: 1,
      constant:0xffffffff, texCoordIndex:0, transformFlags:0},
      {colorOp: 1}]};
  const read = device => {
    const bgra = device.readColor(null).pixels.slice((8*16+8)*4,(8*16+9)*4);
    return [bgra[2],bgra[1],bgra[0],bgra[3]];
  };
  for (const version of [1, 2]) {
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 16;
    const device = new D3D9Backend.Device(canvas, {webglVersion: version});
    try {
      for (const test of cases) {
        const draw = {primitive: 4, primitiveCount: 1, stride: 12,
          vertices: new Uint8Array(new Float32Array([-1,-1,.25, 3,-1,.25, -1,3,.25]).buffer),
          attributes: [{register: 0, usage: 0, usageIndex: 0, type: 2, offset: 0}],
          vertexShader: Uint32Array.from(test.vertexTokens),
          pixelShader: test.pixelTokens ? Uint32Array.from(test.pixelTokens) : null,
          fixedFunction: test.pixelTokens ? undefined : fixed,
          vertexConstants: new Float32Array([1,.25,.5,.75, .1,.8,.3,1]),
          pixelConstants: new Float32Array([1,.25,.5,.75, .1,.8,.3,1]),
          textures: [], state: {zenable: false, zwrite: false, cull: 1}};
        device.clear([31/255,63/255,127/255,1], 1);
        try {
          device.draw(draw);
          results.push({version, test, rgba: read(device)});
        } catch (error) {
          results.push({version, test, error: String(error), diagnostic: error.diagnostic});
        }
      }
      // This is the unchanged native IR from the integrated Start Game failure.
      // Synthetic geometry and constants isolate linkage; they do not replay a scene.
      const constants = new Float32Array(96*4);
      for (let matrix=0;matrix<2;matrix++)for(let c=0;c<4;c++)constants[matrix*16+c*5]=1;
      const draw = {primitive: 4, primitiveCount: 1, stride: 24,
        vertices: new Uint8Array(new Float32Array([-1,-1,.25,0,0,1, 3,-1,.25,0,0,1, -1,3,.25,0,0,1]).buffer),
        attributes: [{register:0,usage:0,usageIndex:0,type:2,offset:0},
          {register:1,usage:3,usageIndex:0,type:2,offset:12}],
        vertexShader:{irVersion:1,nativeBytes:Uint8Array.from(captured.vertex.nativeBytes)},
        pixelShader:null, vertexConstants:constants, textures:[], fixedFunction:fixed,
        state:{zenable:false,zwrite:false,cull:1}};
      device.clear([31/255,63/255,127/255,1],1);
      try {
        device.draw(draw);
        results.push({version,test:{name:'captured-game-VS-with-fixed-factor',rgba:[64,128,255,191]},rgba:read(device)});
      } catch(error) {
        results.push({version,test:{name:'captured-game-VS-with-fixed-factor'},error:String(error),diagnostic:error.diagnostic});
      }
    } finally { device.destroy(); }
  }
  return results;
}"""


def main():
    reference = json.loads((HERE / 'reference/shader-link.json').read_text())
    captured = json.loads((HERE / 'reference/start-game-shader-link.json').read_text())
    # Diffuse defaults agree across native HW/SW vertex processing. Specular
    # alpha differs in that reference and is outside this regression.
    cases = [c for c in reference['cases'] if c['pixelSource'] != 1]
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        try:
            page = browser.new_page()
            for name in ['gpu-backend', 'd3d-shader-ir', 'd3d9-shader', 'd3d9-fixed', 'd3d9-backend']:
                page.add_script_tag(path=str(HERE.parent / 'tools/wine-assembly/lib' / (name + '.js')))
            result = page.evaluate(DRAW, {'cases':cases, 'captured':captured})
        finally:
            browser.close()
    print(json.dumps(result), flush=True)
    for row in result:
        assert 'error' not in row, 'Native-valid shader pair must link: ' + row.get('error', '')
        assert all(abs(a-b) <= 1 for a,b in zip(row['rgba'], row['test']['rgba'])), row
    print(f'PASS {len(result)} WebGL1/2 diffuse-link cases: native reference and captured game shader')


if __name__ == '__main__':
    main()
