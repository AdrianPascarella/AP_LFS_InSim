# Drive a running LFS from the agent for the live test (tests/live_lfs.py), with no human at hand.
#
#   powershell -File tests/lfs_screen.ps1 -Keys "t" -Then "/insim=29999{ENTER}"   type into LFS
#   powershell -File tests/lfs_screen.ps1 -X 1736 -Y 506                         click, then capture
#   powershell -File tests/lfs_screen.ps1                                        capture only
#
# Every call ends with a half-size screenshot in tests/live_reports/screen.png (ignored by git),
# to see where LFS is. -Keys and -Then use SendKeys syntax ({ENTER}, {ESC}...); -Then is sent a
# moment after -Keys, because opening the chat box with "t" takes LFS a little while.
# Coordinates are of the full screen. With LFS full screen at 1920x1080, an InSim button
# (200x200 units) is at x = 420 + L * 5.4, y = T * 5.4.
param([int]$X = -1, [int]$Y = -1, [string]$Keys = "", [string]$Then = "", [int]$Wait = 1500)

Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public static class LfsMouse {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, IntPtr e);
}
"@

$lfs = Get-Process LFS -ErrorAction SilentlyContinue
if ($null -eq $lfs) { Write-Error "LFS is not running"; exit 1 }
if ($X -ge 0 -or $Keys -ne "") {
    $shell = New-Object -ComObject WScript.Shell
    [void]$shell.AppActivate($lfs.Id)
    Start-Sleep -Milliseconds 300
    if ($X -ge 0) {
        [LfsMouse]::SetCursorPos($X, $Y) | Out-Null
        Start-Sleep -Milliseconds 150
        [LfsMouse]::mouse_event(2, 0, 0, 0, [IntPtr]::Zero)  # left button down
        Start-Sleep -Milliseconds 80
        [LfsMouse]::mouse_event(4, 0, 0, 0, [IntPtr]::Zero)  # left button up
    }
    if ($Keys -ne "") { $shell.SendKeys($Keys) }
    if ($Then -ne "") { Start-Sleep -Milliseconds 600; $shell.SendKeys($Then) }
    Start-Sleep -Milliseconds $Wait
}

$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$full = New-Object Drawing.Bitmap $bounds.Width, $bounds.Height
[Drawing.Graphics]::FromImage($full).CopyFromScreen($bounds.Location, [Drawing.Point]::Empty, $bounds.Size)
$half = New-Object Drawing.Bitmap $full, ([int]($bounds.Width / 2)), ([int]($bounds.Height / 2))
$folder = Join-Path $PSScriptRoot "live_reports"
New-Item -ItemType Directory -Force $folder | Out-Null
$half.Save((Join-Path $folder "screen.png"))
