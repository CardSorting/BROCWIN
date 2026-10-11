'use strict';
// Exact original-font cells through the client's CreateFont/TextOut/GetPixel path.
const fs = require('node:fs'), path = require('node:path');
const assert = require('node:assert/strict'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '../..');
const {bootRenderHarness} = require(path.join(root, 'theseus/tools/wine-assembly/test/render-helper'));
const reference = JSON.parse(fs.readFileSync(path.join(__dirname, 'reference/font-phantoms.json')));
(async () => {
  const apis = [['SetTextColor',2],['SetBkColor',2],['TextOutW',5],
    ['GetTextExtentPoint32W',4],['GetPixel',3]];
  const extraWat = apis.map(([name,n]) =>
    `(func (export "probe_${name}") ${Array.from({length:n},(_,i)=>`(param $p${i} i32)`).join(' ')} (result i32)
      (call $handle_${name} ${Array.from({length:5},(_,i)=>i<n?`(local.get $p${i})`:'(i32.const 0)').join(' ')} (i32.const 0))
      (i32.load (global.get $reg_base)))`).join('\n');
  const {exports:e,memory,hostCtx} = await bootRenderHarness({fonts:'all',extraWat});
  e.set_winver(0x1db10106);
  const put = (s,wide=false) => {
    const b=Buffer.from(s+'\0',wide?'utf16le':'latin1'), p=e.guest_alloc(b.length)>>>0;
    new Uint8Array(memory.buffer).set(b,e.guest_to_wasm(p)); return p;
  };
  hostCtx.vfs.dirs.add('c:\\joysword'); hostCtx.vfs.setCurrentDirectory('c:\\joysword');
  for (const input of reference.inputs) {
    const b=fs.readFileSync(path.join(root,'client/data',input.file));
    assert.equal(crypto.createHash('sha256').update(b).digest('hex'),input.originalSha256);
    hostCtx.vfs.files.set('c:\\joysword\\'+input.file,{data:new Uint8Array(b),attrs:32});
    assert.equal(e.test_call_AddFontResourceA(put(input.file)),1);
  }
  const screen=e.test_call_GetDC(0), dc=e.test_call_CreateCompatibleDC(0);
  const bm=e.test_call_CreateCompatibleBitmap(screen,129,129);
  assert(bm); const oldbm=e.test_call_SelectObject(dc,bm), extent=e.guest_alloc(8);
  const blank=put('                    ',true), results=[];
  for (const c of reference.cases) {
    const font=e.test_call_CreateFontW(c.height,0,0,0,c.weight,0,0,0,1,0,0,c.quality,0,put(c.family,true));
    assert(font); const old=e.test_call_SelectObject(dc,font);
    e.probe_SetTextColor(dc,255); e.probe_SetBkColor(dc,0);
    assert.equal(e.probe_TextOutW(dc,0,0,blank,20),1);
    const text=put(c.character,true);
    assert.equal(e.probe_GetTextExtentPoint32W(dc,text,1,extent),1);
    assert.equal(e.probe_TextOutW(dc,0,0,text,1),1);
    const measured=[e.guest_read32(extent)>>>0,e.guest_read32(extent+4)>>>0];
    assert.deepEqual(measured,c.extent,`${c.font} ${c.height} ${c.character} extent`);
    const [w,h]=c.size, pixels=Buffer.alloc(w*h);
    for(let y=0;y<h;y++) for(let x=0;x<w;x++) pixels[y*w+x]=e.probe_GetPixel(dc,x,y)&255;
    results.push({font:c.font,height:c.height,character:c.character,role:c.role,
      pixelsEqual:pixels.equals(Buffer.from(c.pixels,'base64'))});
    e.test_call_SelectObject(dc,old); e.test_call_DeleteObject(font);
  }
  e.test_call_SelectObject(dc,oldbm); e.test_call_DeleteObject(bm); e.test_call_DeleteDC(dc);
  const failures=results.filter(r=>!r.pixelsEqual);
  const report={cases:results.length,regressions:results.filter(r=>r.role==='regression').length,
    nativeExtents:'pass',pixelMatches:results.length-failures.length,failures,
    scope:reference.scope,results};
  if(process.argv[2]) fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({cases:report.cases,regressions:report.regressions,
    pixelMatches:report.pixelMatches,failures:failures.length}));
  assert.equal(failures.length,0,'Every retained native phantom regression/control cell must match');
})().catch(e=>{console.error(e);process.exitCode=1;});
