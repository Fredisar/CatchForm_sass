# Liste toutes les fenetres (y compris masquees) du processus Word le plus recent, avec leurs textes.
$code = @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public static class Win {
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr parent, EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder s, int max);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr hWnd, StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);

    static string Text(IntPtr h) { var s = new StringBuilder(512); GetWindowText(h, s, 512); return s.ToString(); }
    static string Cls(IntPtr h) { var s = new StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }

    public static List<string> Describe(uint targetPid) {
        var lines = new List<string>();
        EnumWindows((h, l) => {
            uint pid; GetWindowThreadProcessId(h, out pid);
            if (pid != targetPid) return true;
            string t = Text(h), c = Cls(h);
            if (t.Length == 0 && c != "#32770" && c != "bosa_sdm_msword" && c != "NUIDialog") return true;
            lines.Add("== '" + t + "' classe=" + c + " visible=" + IsWindowVisible(h));
            EnumChildWindows(h, (ch, l2) => {
                string ct = Text(ch);
                if (ct.Length > 0) lines.Add("     [" + Cls(ch) + "] " + ct);
                return true;
            }, IntPtr.Zero);
            return true;
        }, IntPtr.Zero);
        return lines;
    }
}
"@
Add-Type -TypeDefinition $code
$proc = Get-Process WINWORD | Sort-Object StartTime -Descending | Select-Object -First 1
"Processus Word : $($proc.Id) (demarre a $($proc.StartTime))"
[Win]::Describe([uint32]$proc.Id)
