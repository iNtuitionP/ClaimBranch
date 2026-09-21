// Synthetic file-access exerciser, not an application or authorization broker.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

class IsolationChild
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern IntPtr CreateFileW(string path, uint access, uint share,
        IntPtr security, uint creation, uint flags, IntPtr template);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool WriteFile(IntPtr handle, byte[] data, uint size,
        out uint written, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool ReadFile(IntPtr handle, byte[] data, uint size,
        out uint read, IntPtr overlapped);
    [DllImport("kernel32.dll")]
    static extern bool CloseHandle(IntPtr handle);

    static int Access(string path, bool write, bool create)
    {
        IntPtr handle = CreateFileW(path, write ? 0x40000000u : 0x80000000u,
            0, IntPtr.Zero, create ? 1u : 3u, 0x80, IntPtr.Zero);
        if (handle == new IntPtr(-1)) return Marshal.GetLastWin32Error();
        try
        {
            byte[] data = write ? Encoding.ASCII.GetBytes("synthetic-proposal") : new byte[64];
            uint count;
            bool ok = write ? WriteFile(handle, data, (uint)data.Length, out count, IntPtr.Zero)
                            : ReadFile(handle, data, (uint)data.Length, out count, IntPtr.Zero);
            if (!ok) return Marshal.GetLastWin32Error();
            return count == data.Length || (!write && count > 0) ? 0 : 29;
        }
        finally { CloseHandle(handle); }
    }

    static int Main()
    {
        // No caller-supplied paths, arguments, commands, or authority assertions.
        int accepted = Access("accepted.bin", true, false);
        int manuscript = Access("manuscript.tex", true, false);
        int secret = Access("signing-secret.bin", false, false);
        int proposal = Access("output/proposal.txt", true, true);
        File.WriteAllText("output/result.txt", String.Join(",", new string[] {
            accepted.ToString(), manuscript.ToString(), secret.ToString(), proposal.ToString()
        }));
        return 0;
    }
}
