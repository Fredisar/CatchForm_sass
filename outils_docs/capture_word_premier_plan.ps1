# Met au premier plan les fenetres du Word de test (pas celui de l'utilisateur) et capture l'ecran.
param([int]$UserWordPid = 16392)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$code = @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public static class W {
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint flags);
    public static List<IntPtr> Visible(uint pid) {
        var list = new List<IntPtr>();
        EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p); if (p == pid && IsWindowVisible(h)) list.Add(h); return true; }, IntPtr.Zero);
        return list;
    }
    public static string Describe(IntPtr h) {
        var t = new StringBuilder(512); GetWindowText(h, t, 512);
        var c = new StringBuilder(256); GetClassName(h, c, 256);
        return "'" + t + "' classe=" + c;
    }
}
"@
Add-Type -TypeDefinition $code
$proc = Get-Process WINWORD | Where-Object { $_.Id -ne $UserWordPid } | Sort-Object StartTime -Descending | Select-Object -First 1
if (-not $proc) { "Aucun Word de test en cours."; exit }
"Word de test : $($proc.Id) demarre a $($proc.StartTime)"
$wins = [W]::Visible([uint32]$proc.Id)
foreach ($h in $wins) {
    "Fenetre visible : " + [W]::Describe($h)
    [W]::ShowWindow($h, 9) | Out-Null                       # SW_RESTORE
    [W]::SetWindowPos($h, [IntPtr](-1), 0, 0, 0, 0, 0x0003) | Out-Null   # HWND_TOPMOST, sans deplacer
}
Start-Sleep -Seconds 2
$shot = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "capture_word.png"
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save($shot, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
foreach ($h in $wins) { [W]::SetWindowPos($h, [IntPtr](-2), 0, 0, 0, 0, 0x0003) | Out-Null }   # retire le premier plan force
"Capture : $shot"
