'use strict';
// Exercise the shipped D3D9 publication and renderer with real canvas pixels.
// Present(NULL,NULL,NULL,NULL) fills the device window's client rectangle.
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '../tools/wine-assembly');
const {Canvas} = require(path.join(root, 'lib/canvas-compat'));
const {Win98Renderer} = require(path.join(root, 'lib/renderer'));
const {Bridge} = require(path.join(root, 'lib/d3d9-host'));
const canvas = new Canvas(100, 80), renderer = new Win98Renderer(canvas);
// Window paint is already completed, as it is when the frame is composited.
renderer.drawWindow = () => {};
renderer.scheduleRepaint = () => {};
const win = {hwnd:1,x:10,y:8,w:28,h:22,visible:true,style:0x10c00000,
  clientRect:{x:14,y:15,w:20,h:12},_backCanvas:new Canvas(28,22)};
renderer.windows[1] = win;
const gray = [120,120,120,255], red = [255,0,0,255], blue = [0,0,255,255];
const fill=(c,color)=>{const x=c.getContext('2d');x.fillStyle=color;x.fillRect(0,0,c.width,c.height);};
fill(win._backCanvas,'rgb(120,120,120)');
const frame = new Canvas(10,6);fill(frame,'#ff0000');
const entry = {win,layer:{canvas:null,kind:'gpu',writeSeq:0}};
const bridge = new Bridge({backend:'webgl',renderer:()=>renderer});
const pixel=(c,x,y)=>[...c.getContext('2d').getImageData(x,y,1,1).data];
const check=(c,ox,oy)=>{
  assert.deepEqual(pixel(c,ox,oy),gray,'caption is preserved');
  assert.deepEqual(pixel(c,ox+3,oy+7),gray,'left border is preserved');
  assert.deepEqual(pixel(c,ox+4,oy+7),red,'first texel lands at client origin');
  assert.deepEqual(pixel(c,ox+23,oy+18),red,'Present stretches to the last client pixel');
  assert.deepEqual(pixel(c,ox+24,oy+18),gray,'right border is preserved');
  assert.deepEqual(pixel(c,ox+4,oy+19),gray,'bottom border is preserved');
};
bridge._publishGPU(entry,{canvas:frame});renderer.repaint();check(canvas,10,8);
// The same placement must be used by screenshots/post-processing.
check(renderer._buildExclusivePresentationSource(win,[win],0),0,0);
// Moving changes screen coordinates, not the frame's client-relative origin.
win.x=37;win.y=31;win.clientRect={x:41,y:38,w:20,h:12};
renderer.repaint();check(canvas,37,31);
// Geometry can change between presents without a new GPU frame.
win.clientRect={x:39,y:36,w:24,h:14};renderer.repaint();
assert.deepEqual(pixel(canvas,39,36),red);
assert.deepEqual(pixel(canvas,62,49),red);
assert.deepEqual(pixel(canvas,63,49),gray);
// Reusing a mutable presentation canvas must still expose each completed frame.
fill(frame,'#0000ff');bridge._publishGPU(entry,{canvas:frame});renderer.repaint();
assert.deepEqual(pixel(canvas,39,36),blue);
assert.deepEqual(pixel(canvas,62,49),blue);
// Other APIs already publish window-relative layers; their origin stays put.
const legacy={canvas:frame,kind:'dx',writeSeq:1};win._dxFrameLayer=legacy;
assert.equal(renderer._overlayFrameLayer(win),legacy);
const gl={canvas:frame,kind:'gpu',writeSeq:1,mergedIntoWindow:true};win._dxFrameLayer=gl;
assert.equal(renderer._overlayFrameLayer(win),null,'merged OpenGL output is not drawn twice');
// USER keeps child window positions parent-relative, but client rectangles
// are absolute. A child D3D device must subtract the actual screen origin.
const child = {hwnd:2,x:5,y:6,w:12,h:10,isChild:true,parentHwnd:1,visible:true,
  style:0x50000000,clientRect:{x:46,y:44,w:8,h:6},_backCanvas:new Canvas(12,10),
  wasm:{exports:{wnd_window_screen_x:()=>44,wnd_window_screen_y:()=>42}}};
renderer.windows[2]=child;fill(child._backCanvas,'rgb(120,120,120)');
const childEntry={win:child,layer:{kind:'gpu',writeSeq:0}};
bridge._publishGPU(childEntry,{canvas:frame});renderer.repaint();
assert.deepEqual(pixel(canvas,44,42),gray,'child border stays visible');
assert.deepEqual(pixel(canvas,46,44),blue,'child uses absolute USER client origin');
assert.deepEqual(pixel(canvas,53,49),blue,'child fills client extent');
assert.deepEqual(pixel(canvas,54,49),gray,'child right border stays visible');
console.log('PASS D3D9 client origin, stretch, window move, geometry change, fresh frames, composition and legacy layers');
