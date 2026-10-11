'use strict';
// Independent runtime work, using constructed shaders/texture blocks.
// This is not a client-startup or gameplay performance measurement.
const assert=require('assert');
const {performance}=require('perf_hooks');
const Shader=require('../tools/wine-assembly/lib/d3d9-shader');
const Texture=require('../tools/wine-assembly/lib/d3d9-texture');
const {ArtifactCache}=require('../tools/wine-assembly/lib/validated-artifact-cache');
const words=Uint32Array.from([0xfffe0101,1,0xc00f0000,0x90e40000,65535]);
const bytes=new Uint8Array(64*64/16*8);
for(let i=0;i<bytes.length;i+=8){bytes[i+1]=248;bytes[i+4]=0x55;}
const compile=Shader.compile,decode=Texture.decode;
function measure(fn,n){for(let i=0;i<20;i++)fn();const t=performance.now();for(let i=0;i<n;i++)fn();return performance.now()-t;}
const controlShader=compile(words),controlTexture=decode(bytes,64,64,Texture.DXT1);
const repetitions=2000;
const control={shader:measure(()=>compile(words),repetitions),texture:measure(()=>decode(bytes,64,64,Texture.DXT1),repetitions)};
const cache=new ArtifactCache('constructed-fixtures-v1',null);cache.install(Shader,Texture);
const t=performance.now();assert.deepStrictEqual(Shader.compile(words),controlShader);
assert.deepStrictEqual(Texture.decode(bytes,64,64,Texture.DXT1),controlTexture);
const populate=performance.now()-t;
const warm={shader:measure(()=>Shader.compile(words),repetitions),texture:measure(()=>Texture.decode(bytes,64,64,Texture.DXT1),repetitions)};
console.log(JSON.stringify({schema:'brocwin.artifact-benchmark/v1',engine:process.versions,
  workload:'2000 constructed VS1.1 translations / 64x64 DXT1 conversions; owned results; no client input',
  repetitions,controlMs:control,warmMs:warm,populateWithEqualityChecksMs:populate,
  speedup:{shader:control.shader/warm.shader,texture:control.texture/warm.texture},stats:cache.stats},null,2));
