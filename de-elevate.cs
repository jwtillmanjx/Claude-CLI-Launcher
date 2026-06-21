using System;
using System.Runtime.InteropServices;


/// <summary>
/// Launches a command at standard-user integrity level (non-admin) even when
/// the caller is elevated.  Finds the shell window (Explorer.exe, which always
/// runs non-elevated), duplicates its process token, and uses
/// CreateProcessWithTokenW to start the child with that non-admin token.
///
/// Usage:  de-elevate.exe <command> [args...]
/// Example: de-elevate.exe cmd /c "C:\temp\launch.cmd"
/// </summary>
class DeElevate
{
    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool OpenProcessToken(
        IntPtr hProcess, uint dwAccess, out IntPtr hToken);


    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool DuplicateTokenEx(
        IntPtr hExisting, uint dwAccess, IntPtr lpAttribs,
        int impLevel, int tokenType, out IntPtr hNew);


    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateProcessWithTokenW(
        IntPtr hToken, uint dwLogonFlags, string lpApp, string lpCmd,
        uint dwFlags, IntPtr lpEnv, string lpDir,
        ref STARTUPINFO si, out PROCESS_INFORMATION pi);


    [DllImport("kernel32.dll", SetLastError = true)]
    static extern IntPtr OpenProcess(uint dwAccess, bool bInherit, uint dwPid);


    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr h);


    [DllImport("user32.dll")]
    static extern IntPtr GetShellWindow();


    [DllImport("user32.dll", SetLastError = true)]
    static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwPid);


    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct STARTUPINFO
    {
        public int cb;
        public string lpReserved, lpDesktop, lpTitle;
        public int dwX, dwY, dwXSize, dwYSize;
        public int dwXCountChars, dwYCountChars;
        public int dwFillAttribute, dwFlags;
        public short wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }


    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION
    {
        public IntPtr hProcess, hThread;
        public int dwProcessId, dwThreadId;
    }


    const uint TOKEN_DUPLICATE = 0x0002;
    const uint TOKEN_QUERY = 0x0008;
    const uint TOKEN_ASSIGN_PRIMARY = 0x0001;
    const uint TOKEN_ADJUST_DEFAULT = 0x0080;
    const uint TOKEN_ADJUST_SESSIONID = 0x0100;
    const uint PROCESS_QUERY_INFORMATION = 0x0400;
    const uint CREATE_NEW_CONSOLE = 0x00000010;


    static int Main(string[] args)
    {
        string commandLine = ExtractChildCommandLine();
        if (commandLine == null)
        {
            Console.Error.WriteLine("Usage: de-elevate <command> [args...]");
            return 1;
        }


        // Find the desktop shell window (owned by Explorer.exe, non-elevated)
        IntPtr hShell = GetShellWindow();
        if (hShell == IntPtr.Zero)
            return Fail("GetShellWindow returned null — no desktop shell found");


        uint explorerPid;
        GetWindowThreadProcessId(hShell, out explorerPid);
        if (explorerPid == 0)
            return Fail("Could not get Explorer PID from shell window");


        IntPtr hProc = IntPtr.Zero, hToken = IntPtr.Zero, hDup = IntPtr.Zero;
        try
        {
            hProc = OpenProcess(PROCESS_QUERY_INFORMATION, false, explorerPid);
            if (hProc == IntPtr.Zero)
                return Fail("OpenProcess(explorer pid=" + explorerPid + ")");


            if (!OpenProcessToken(hProc, TOKEN_DUPLICATE, out hToken))
                return Fail("OpenProcessToken(explorer)");


            uint dupAccess = TOKEN_QUERY | TOKEN_ASSIGN_PRIMARY | TOKEN_DUPLICATE
                           | TOKEN_ADJUST_DEFAULT | TOKEN_ADJUST_SESSIONID;
            if (!DuplicateTokenEx(hToken, dupAccess, IntPtr.Zero,
                    2 /* SecurityImpersonation */, 1 /* TokenPrimary */, out hDup))
                return Fail("DuplicateTokenEx");


            var si = new STARTUPINFO();
            si.cb = Marshal.SizeOf(si);
            PROCESS_INFORMATION pi;


            if (!CreateProcessWithTokenW(hDup, 0, null, commandLine,
                    CREATE_NEW_CONSOLE, IntPtr.Zero, null, ref si, out pi))
                return Fail("CreateProcessWithTokenW");


            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
            return 0;
        }
        finally
        {
            if (hDup != IntPtr.Zero) CloseHandle(hDup);
            if (hToken != IntPtr.Zero) CloseHandle(hToken);
            if (hProc != IntPtr.Zero) CloseHandle(hProc);
        }
    }


    static string ExtractChildCommandLine()
    {
        string raw = Environment.CommandLine;
        int pos;
        if (raw.StartsWith("\""))
            pos = raw.IndexOf('"', 1) + 1;
        else
            pos = raw.IndexOf(' ');


        if (pos < 0 || pos >= raw.Length) return null;
        string cmd = raw.Substring(pos).TrimStart();
        return string.IsNullOrEmpty(cmd) ? null : cmd;
    }


    static int Fail(string msg)
    {
        Console.Error.WriteLine(msg + " — error " + Marshal.GetLastWin32Error());
        return 1;
    }
}
