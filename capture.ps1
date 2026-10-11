param([string]$Name = 'native-client', [switch]$Screen)
$ErrorActionPreference = 'Stop'
$TheseusRoot = Split-Path -Parent $PSScriptRoot
$ClientPath = Join-Path $TheseusRoot 'client\data\x2.exe'
$ClientProcess = Get-Process x2 -ErrorAction Stop | Where-Object { $_.Path -eq $ClientPath } | Select-Object -First 1
if (-not $ClientProcess -or $ClientProcess.MainWindowHandle -eq 0) { throw 'The copied client has no main window yet.' }
if ($Name -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid capture name.' }
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class TheseusCapture {
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd,out Rect rect);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd,IntPtr dc,uint flags);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
}
"@
$ClientRect = New-Object TheseusCapture+Rect
[TheseusCapture]::GetWindowRect($ClientProcess.MainWindowHandle,[ref]$ClientRect) | Out-Null
$CaptureBitmap = New-Object System.Drawing.Bitmap ($ClientRect.Right-$ClientRect.Left),($ClientRect.Bottom-$ClientRect.Top)
$CaptureGraphics = [System.Drawing.Graphics]::FromImage($CaptureBitmap)
try {
  if ($Screen) {
    [TheseusCapture]::SetForegroundWindow($ClientProcess.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 500
    $CaptureGraphics.CopyFromScreen($ClientRect.Left,$ClientRect.Top,0,0,$CaptureBitmap.Size)
  } else {
    $CaptureDc = $CaptureGraphics.GetHdc()
    try { [TheseusCapture]::PrintWindow($ClientProcess.MainWindowHandle,$CaptureDc,2) | Out-Null }
    finally { $CaptureGraphics.ReleaseHdc($CaptureDc) }
  }
  $CaptureDirectory = Join-Path $PSScriptRoot 'reports'
  New-Item -ItemType Directory -Path $CaptureDirectory -Force | Out-Null
  $CapturePath = Join-Path $CaptureDirectory "$Name.png"
  $CaptureBitmap.Save($CapturePath,[System.Drawing.Imaging.ImageFormat]::Png)
  Write-Output $CapturePath
} finally { $CaptureGraphics.Dispose(); $CaptureBitmap.Dispose() }
