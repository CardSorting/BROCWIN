# Run in SysWOW64 PowerShell: native API reference only, never the game client.
$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class CryptoReference {
  [DllImport("advapi32",CharSet=CharSet.Ansi,SetLastError=true)] static extern bool CryptAcquireContextA(IntPtr output,string container,string provider,uint type,uint flags);
  [DllImport("advapi32",SetLastError=true)] static extern bool CryptGenRandom(IntPtr provider,uint length,IntPtr output);
  [DllImport("advapi32",SetLastError=true)] static extern bool CryptReleaseContext(IntPtr provider,uint flags);
  [DllImport("kernel32",SetLastError=true)] static extern void SetLastError(uint error);
  static IntPtr current;
  static Dictionary<string,object> Result(bool ok) {
    uint error=unchecked((uint)Marshal.GetLastWin32Error());
    return new Dictionary<string,object>{{"result",ok?1:0},{"error",error}};
  }
  public static object Acquire(string container,string provider,uint type,uint flags,bool nullOutput) {
    if(container=="")container=null;
    if(provider=="")provider=null;
    IntPtr output=Marshal.AllocHGlobal(IntPtr.Size);
    try {
      Marshal.WriteIntPtr(output,new IntPtr(0x1234));SetLastError(0x1234);
      bool ok=CryptAcquireContextA(nullOutput?IntPtr.Zero:output,container,provider,type,flags);
      var row=Result(ok);IntPtr handle=Marshal.ReadIntPtr(output);
      row["output"]=ok?(object)"handle":handle==IntPtr.Zero?null:(object)handle.ToInt64();
      if(ok)CryptReleaseContext(handle,0);
      return row;
    } finally {Marshal.FreeHGlobal(output);}
  }
  public static void Fresh() {
    IntPtr output=Marshal.AllocHGlobal(IntPtr.Size);
    try {
      if(!CryptAcquireContextA(output,null,null,1,0xf0000000))throw new Exception("Ephemeral provider failed");
      current=Marshal.ReadIntPtr(output);
    } finally {Marshal.FreeHGlobal(output);}
  }
  public static object Random(string name) {
    const int n=131089;
    byte[] bytes=new byte[n];for(int i=0;i<n;i++)bytes[i]=0xa5;
    IntPtr output=Marshal.AllocHGlobal(n);
    try {
      Marshal.Copy(bytes,0,output,n);
      uint size=(uint)(name.Contains("zero")?0:name=="large"?n:16);
      IntPtr provider=name.StartsWith("invalid")?IntPtr.Zero:current;
      IntPtr destination=name.Contains("null")?IntPtr.Zero:output;
      SetLastError(0x1234);
      bool ok=CryptGenRandom(provider,size,destination);
      var row=Result(ok);Marshal.Copy(output,bytes,0,n);
      bool changed=false;foreach(byte b in bytes)if(b!=0xa5)changed=true;
      if(name!="released")row["changed"]=changed;
      return row;
    } finally {Marshal.FreeHGlobal(output);}
  }
  public static object Release(string name,uint flags) {
    if(name=="fresh")Fresh();
    SetLastError(0x1234);
    return Result(CryptReleaseContext(name=="null"?IntPtr.Zero:current,flags));
  }
}
'@
$cryptoInput = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'reference/crypto.json') -Raw | ConvertFrom-Json
$cryptoRows = @()
[CryptoReference]::Fresh()
foreach ($cryptoCase in $cryptoInput.cases) {
    $cryptoRow = [ordered]@{api=$cryptoCase.api;case=$cryptoCase.case}
    if ($cryptoCase.api -eq 'acquire') {
        $cryptoContainer = if ($null -eq $cryptoCase.container) { $null } else { [string]$cryptoCase.container }
        $cryptoProvider = if ($null -eq $cryptoCase.provider) { $null } else { [string]$cryptoCase.provider }
        # PowerShell marshals $null string parameters to an empty string. A
        # C# wrapper converts those empty strings back to native NULL.
        $cryptoResult = [CryptoReference]::Acquire($cryptoContainer,$cryptoProvider,$cryptoCase.type,$cryptoCase.flags,$cryptoCase.nullOutput)
    } elseif ($cryptoCase.api -eq 'random') {
        $cryptoResult = [CryptoReference]::Random($cryptoCase.case)
    } else {
        $cryptoResult = [CryptoReference]::Release($cryptoCase.case,$cryptoCase.flags)
    }
    foreach ($cryptoKey in $cryptoResult.Keys) { $cryptoRow[$cryptoKey]=$cryptoResult[$cryptoKey] }
    $cryptoRows += [pscustomobject]$cryptoRow
}
[ordered]@{
  scope='Local P/Invoke CryptoAPI ephemeral reference; no saved keys or game execution'
  pointerBits=[IntPtr]::Size*8
  sourceSha256=(Get-FileHash -LiteralPath (Join-Path $env:WINDIR $(if ([IntPtr]::Size -eq 4) {'SysWOW64/advapi32.dll'} else {'System32/advapi32.dll'})) -Algorithm SHA256).Hash.ToLowerInvariant()
  cases=$cryptoRows
} | ConvertTo-Json -Depth 8
