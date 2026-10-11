# Run with SysWOW64 Windows PowerShell. Hidden D3D9 reference, never x2.exe.
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class ResetReference {
  [StructLayout(LayoutKind.Sequential)] public struct PP {
    public uint width,height,format,count,ms,quality,swap;
    public IntPtr window;
    public uint windowed,depth,depthFormat,flags,refresh,interval;
    public uint[] Words() { return new uint[]{width,height,format,count,ms,quality,swap,windowed,depth,depthFormat,flags,refresh,interval}; }
  }
  [DllImport("user32", CharSet=CharSet.Unicode)] static extern IntPtr CreateWindowExW(uint ex,string cls,string title,uint style,int x,int y,int w,int h,IntPtr parent,IntPtr menu,IntPtr instance,IntPtr arg);
  [DllImport("user32")] static extern bool DestroyWindow(IntPtr window);
  [DllImport("d3d9")] static extern IntPtr Direct3DCreate9(uint version);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate uint Release(IntPtr obj);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Create(IntPtr obj,uint adapter,uint type,IntPtr window,uint flags,ref PP pp,out IntPtr device);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Reset(IntPtr obj,ref PP pp);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Chain(IntPtr obj,uint index,out IntPtr chain);
  static T Method<T>(IntPtr obj,int index) { return (T)(object)Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(Marshal.ReadIntPtr(obj),index*IntPtr.Size),typeof(T)); }
  static void Check(int hr) { if(hr<0) Marshal.ThrowExceptionForHR(hr); }
  public static object[] Run() {
    if(IntPtr.Size!=4) throw new Exception("Use the 32-bit PowerShell host");
    IntPtr window=CreateWindowExW(0,"STATIC","Theseus Reset reference",0,0,0,320,240,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero);
    if(window==IntPtr.Zero) throw new Exception("Hidden reference window failed");
    IntPtr root=Direct3DCreate9(32), device=IntPtr.Zero;
    var rows=new List<object>();
    try {
      PP pp=new PP {width=320,height=240,format=22,count=1,swap=1,window=window,windowed=1,interval=0x80000000};
      Check(Method<Create>(root,16)(root,0,1,window,0x20,ref pp,out device));
      string[] names={"explicit","automatic","different-extent","captured-flags"};
      uint[][] cases={new uint[]{320,240,22,1,0},new uint[]{0,0,0,0,0},new uint[]{128,96,21,2,0},new uint[]{0,0,22,2,3}};
      for(int i=0;i<cases.Length;i++) {
        uint[] c=cases[i];
        pp=new PP {width=c[0],height=c[1],format=c[2],count=c[3],swap=1,window=window,windowed=1,depth=1,depthFormat=77,flags=c[4],interval=0x80000000};
        uint[] before=pp.Words();
        uint result=unchecked((uint)Method<Reset>(device,16)(device,ref pp));
        IntPtr chain;Check(Method<Chain>(device,14)(device,0,out chain));
        PP stored=new PP();
        try {Check(Method<Reset>(chain,9)(chain,ref stored));} finally {Method<Release>(chain,2)(chain);}
        rows.Add(new {name=names[i],before=before,result=result,after=pp.Words(),stored=stored.Words()});
      }
    } finally {
      if(device!=IntPtr.Zero)Method<Release>(device,2)(device);
      if(root!=IntPtr.Zero)Method<Release>(root,2)(root);
      DestroyWindow(window);
    }
    return rows.ToArray();
  }
}
'@
$resetResult = [ResetReference]::Run()
[ordered]@{
  scope = 'Local 32-bit D3D9 Reset writeback in hidden reference window; no game execution'
  pointerBits = [IntPtr]::Size * 8
  sourceSha256 = (Get-FileHash -LiteralPath "$env:WINDIR/SysWOW64/d3d9.dll" -Algorithm SHA256).Hash.ToLowerInvariant()
  fields = @('width','height','format','count','ms','quality','swap','windowed','depth','depthFormat','flags','refresh','interval')
  cases = $resetResult
} | ConvertTo-Json -Depth 8
