param([int]$ClickX = -1, [int]$ClickY = -1, [string]$Keys = '', [int]$HoldKey = -1, [ValidateRange(20,5000)][int]$HoldMs = 120, [int[]]$SequenceKeys = @())
$ErrorActionPreference = 'Stop'
$TheseusRoot = Split-Path -Parent $PSScriptRoot
$ClientPath = Join-Path $TheseusRoot 'client\data\x2.exe'
$ClientProcess = Get-Process x2 -ErrorAction Stop | Where-Object { $_.Path -eq $ClientPath } | Select-Object -First 1
if (-not $ClientProcess -or $ClientProcess.MainWindowHandle -eq 0) { throw 'The copied client has no main window.' }
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class TheseusInput {
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd,out Rect rect);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint dx,uint dy,uint data,UIntPtr extra);
  [DllImport("user32.dll")] public static extern void keybd_event(byte key,byte scan,uint flags,UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint key,uint kind);
}
"@
$TheseusShell = New-Object -ComObject WScript.Shell
$TheseusShell.AppActivate($ClientProcess.Id) | Out-Null
[TheseusInput]::SetForegroundWindow($ClientProcess.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 250
if ([TheseusInput]::GetForegroundWindow() -ne $ClientProcess.MainWindowHandle) { throw 'Copied client did not receive focus; input not sent.' }
if ($ClickX -ge 0 -and $ClickY -ge 0) {
  $ClientRect = New-Object TheseusInput+Rect
  [TheseusInput]::GetWindowRect($ClientProcess.MainWindowHandle,[ref]$ClientRect) | Out-Null
  if ($ClickX -ge ($ClientRect.Right-$ClientRect.Left) -or $ClickY -ge ($ClientRect.Bottom-$ClientRect.Top)) { throw 'Click lies outside copied client.' }
  [TheseusInput]::SetCursorPos($ClientRect.Left+$ClickX,$ClientRect.Top+$ClickY) | Out-Null
  [TheseusInput]::mouse_event(2,0,0,0,[UIntPtr]::Zero)
  Start-Sleep -Milliseconds 80
  [TheseusInput]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
}
if ($Keys) { $TheseusShell.SendKeys($Keys) }
$TheseusKeySequence = @()
if ($HoldKey -ge 0 -and $HoldKey -le 255) { $TheseusKeySequence += $HoldKey }
$TheseusKeySequence += $SequenceKeys
foreach ($HoldKey in $TheseusKeySequence) {
  if ($HoldKey -lt 0 -or $HoldKey -gt 255) { throw 'Invalid key code.' }
  $KeyFlags = if ($HoldKey -in @(37,38,39,40)) { 1 } else { 0 }
  $KeyScan = [byte][TheseusInput]::MapVirtualKey($HoldKey,0)
  try {
    [TheseusInput]::keybd_event([byte]$HoldKey,$KeyScan,$KeyFlags,[UIntPtr]::Zero)
    Start-Sleep -Milliseconds $HoldMs
  } finally { [TheseusInput]::keybd_event([byte]$HoldKey,$KeyScan,($KeyFlags -bor 2),[UIntPtr]::Zero) }
  Start-Sleep -Milliseconds 100
}
