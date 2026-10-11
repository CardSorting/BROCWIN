# Native loopback API reference; run in SysWOW64 PowerShell for the x86 ABI.
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
public static class WinsockIoReference {
  [StructLayout(LayoutKind.Sequential)] struct Buffer {public uint length;public IntPtr pointer;public Buffer(uint n,IntPtr p){length=n;pointer=p;}}
  [DllImport("ws2_32",SetLastError=true)] static extern int WSARecv(IntPtr s,[In] Buffer[] buffers,uint n,ref uint count,ref uint flags,IntPtr ov,IntPtr callback);
  [DllImport("ws2_32",SetLastError=true)] static extern int WSASend(IntPtr s,[In] Buffer[] buffers,uint n,ref uint count,uint flags,IntPtr ov,IntPtr callback);
  [DllImport("ws2_32",SetLastError=true)] static extern int WSAGetOverlappedResult(IntPtr s,IntPtr ov,ref uint count,int wait,ref uint flags);
  [DllImport("ws2_32")] static extern IntPtr WSACreateEvent();
  [DllImport("ws2_32")] static extern int WSACloseEvent(IntPtr e);
  [DllImport("kernel32")] static extern uint WaitForSingleObject(IntPtr e,uint milliseconds);
  [DllImport("kernel32")] static extern bool ResetEvent(IntPtr e);
  [DllImport("kernel32")] static extern bool SetEvent(IntPtr e);
  [DllImport("kernel32")] static extern void SetLastError(uint error);
  static uint count,flags;
  static IntPtr ov,evt,storage;
  static List<object> rows;
  static void Init() {
    for(int i=0;i<IntPtr.Size*3+8;i+=4)Marshal.WriteInt32(ov,i,0);
    Marshal.WriteIntPtr(ov,IntPtr.Size*2+8,evt);count=0x1234;flags=0;ResetEvent(evt);
  }
  static void Take(string label,int result) {
    int error=Marshal.GetLastWin32Error();
    rows.Add(new Dictionary<string,object>{{"case",label},{"result",result},{"error",error},
      {"count",count},{"flags",flags},{"internal",unchecked((uint)Marshal.ReadIntPtr(ov).ToInt64())},
      {"transferred",unchecked((uint)Marshal.ReadIntPtr(ov,IntPtr.Size).ToInt64())},{"event",WaitForSingleObject(evt,0)}});
  }
  static void Wait() {if(WaitForSingleObject(evt,2000)!=0)throw new Exception("Native I/O timed out");}
  public static object Run() {
    rows=new List<object>();ov=Marshal.AllocHGlobal(IntPtr.Size*3+8);storage=Marshal.AllocHGlobal(32);evt=WSACreateEvent();
    try {
      using(var listener=new Socket(AddressFamily.InterNetwork,SocketType.Stream,ProtocolType.Tcp))
      using(var client=new Socket(AddressFamily.InterNetwork,SocketType.Stream,ProtocolType.Tcp)) {
        listener.Bind(new IPEndPoint(IPAddress.Loopback,0));listener.Listen(1);client.Connect(listener.LocalEndPoint);
        using(var peer=listener.Accept()) {
          IntPtr raw=client.Handle;
          Buffer[] vec={new Buffer(3,storage),new Buffer(5,IntPtr.Add(storage,3))};Init();SetLastError(0x1234);
          Take("receive-pending",WSARecv(raw,vec,2,ref count,ref flags,ov,IntPtr.Zero));
          count=0x1234;flags=0x4321;SetLastError(0x1234);
          Take("pending-query",WSAGetOverlappedResult(raw,ov,ref count,0,ref flags));
          vec[0].length=vec[1].length=0;peer.Send(new byte[]{97,98,99,100,101,102});Wait();SetLastError(0x1234);
          Take("receive-complete",WSAGetOverlappedResult(raw,ov,ref count,0,ref flags));
          byte[] data=new byte[6];Marshal.Copy(storage,data,0,6);
          if(System.Text.Encoding.ASCII.GetString(data)!="abcdef")throw new Exception("Descriptor capture failed");
          Init();vec[0].length=vec[1].length=3;SetLastError(0x1234);
          Take("send-complete",WSASend(raw,vec,2,ref count,0,ov,IntPtr.Zero));
          if(peer.Receive(data)!=6)throw new Exception("Send length");
          count=0x1234;flags=0x4321;SetLastError(0x1234);
          Take("send-query",WSAGetOverlappedResult(raw,ov,ref count,0,ref flags));
          Init();vec[0].length=vec[1].length=0;SetLastError(0x1234);
          Take("zero-receive-pending",WSARecv(raw,vec,2,ref count,ref flags,ov,IntPtr.Zero));
          peer.Send(new byte[]{90});Wait();SetLastError(0x1234);
          Take("zero-receive-complete",WSAGetOverlappedResult(raw,ov,ref count,0,ref flags));
          if(client.Receive(data,1,SocketFlags.None)!=1||data[0]!=90)throw new Exception("Zero receive consumed data");
          Init();vec[0].length=3;SetLastError(0x1234);
          Take("close-pending",WSARecv(raw,vec,1,ref count,ref flags,ov,IntPtr.Zero));
          client.Close();Wait();count=0x1234;flags=0x4321;SetLastError(0x1234);
          Take("close-query",WSAGetOverlappedResult(raw,ov,ref count,0,ref flags));
        }
      }
      return rows;
    } finally {WSACloseEvent(evt);Marshal.FreeHGlobal(storage);Marshal.FreeHGlobal(ov);}
  }
}
'@
$winsockRows = [WinsockIoReference]::Run()
$winsockBits = [IntPtr]::Size * 8
$winsockDll = if ($winsockBits -eq 32) { 'C:/Windows/SysWOW64/ws2_32.dll' } else { 'C:/Windows/System32/ws2_32.dll' }
$winsockOutput = [ordered]@{
    scope = 'Native overlapped event I/O on temporary loopback sockets; no game client execution'
    pointerBits = $winsockBits
    sourceSha256 = (Get-FileHash -LiteralPath $winsockDll -Algorithm SHA256).Hash.ToLowerInvariant()
    cases = @($winsockRows)
}
$winsockName = if ($winsockBits -eq 32) { 'winsock-overlapped-x86.json' } else { 'winsock-overlapped-pinvoke-x64.json' }
$winsockJson = $winsockOutput | ConvertTo-Json -Depth 8
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('reference/' + $winsockName)), $winsockJson + "`n", (New-Object Text.UTF8Encoding $false))
Write-Output $winsockJson
