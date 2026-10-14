// GPL-3.0-or-later. Read the unchanged game's Windows debug output.
// This does not attach a debugger, read game memory, or change game threads.
using System;
using System.Diagnostics;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Text;
using System.Threading;

public static class ReachDebugLog {
    static string Quote(string value) {
        // CommandLineToArgvW quoting, including trailing backslashes.
        StringBuilder result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char c in value) {
            if (c == '\\') { slashes++; continue; }
            if (c == '"') {
                result.Append('\\', slashes * 2 + 1);
                result.Append(c);
            } else {
                result.Append('\\', slashes);
                result.Append(c);
            }
            slashes = 0;
        }
        result.Append('\\', slashes * 2);
        return result.Append('"').ToString();
    }

    public static int Main(string[] args) {
        if (args.Length < 2) {
            Console.Error.WriteLine("Usage: ReachDebugLog.exe game-exe debug-log [game arguments]");
            return 2;
        }
        try {
            string executable = Path.GetFullPath(args[0]);
            string log = Path.GetFullPath(args[1]);
            if (!File.Exists(executable)) throw new FileNotFoundException("Game executable not found", executable);
            StringBuilder command = new StringBuilder();
            for (int i = 2; i < args.Length; i++) {
                if (i > 2) command.Append(' ');
                command.Append(Quote(args[i]));
            }
            // OutputDebugString's documented DBWIN protocol: DWORD PID, ANSI text.
            // Refuse to take over an existing listener (for example DebugView).
            using (MemoryMappedFile buffer = MemoryMappedFile.CreateNew("DBWIN_BUFFER", 4096, MemoryMappedFileAccess.ReadWrite))
            using (MemoryMappedViewAccessor view = buffer.CreateViewAccessor(0, 4096, MemoryMappedFileAccess.ReadWrite))
            using (EventWaitHandle ready = new EventWaitHandle(false, EventResetMode.AutoReset, "DBWIN_BUFFER_READY"))
            using (EventWaitHandle data = new EventWaitHandle(false, EventResetMode.AutoReset, "DBWIN_DATA_READY"))
            using (StreamWriter writer = new StreamWriter(log, false, new UTF8Encoding(false))) {
                writer.AutoFlush = true;
                writer.WriteLine("Reach debug capture r2 (Windows OutputDebugString; original engine)");
                writer.WriteLine("Executable: " + executable);
                writer.WriteLine("Started UTC: " + DateTime.UtcNow.ToString("o"));
                ProcessStartInfo start = new ProcessStartInfo(executable, command.ToString());
                start.WorkingDirectory = Path.GetDirectoryName(executable);
                start.UseShellExecute = false;
                ready.Set();
                using (Process game = Process.Start(start)) {
                    writer.WriteLine("Game PID: " + game.Id);
                    Console.WriteLine("Capturing this game's debug messages to " + log);
                    byte[] text = new byte[4092];
                    bool finished = false;
                    DateTime drainUntil = DateTime.MaxValue;
                    while (true) {
                        if (data.WaitOne(250)) {
                            uint pid = view.ReadUInt32(0);
                            view.ReadArray(4, text, 0, text.Length);
                            // Release the shared buffer promptly, before file I/O.
                            ready.Set();
                            // Never collect messages from other processes.
                            if (pid == (uint)game.Id) {
                                int length = Array.IndexOf(text, (byte)0);
                                if (length < 0) length = text.Length;
                                writer.Write(Encoding.Default.GetString(text, 0, length));
                            }
                        } else if (finished) {
                            break;
                        }
                        if (!finished && game.HasExited) {
                            finished = true;
                            drainUntil = DateTime.UtcNow.AddMilliseconds(250);
                        }
                        if (finished && DateTime.UtcNow >= drainUntil) break;
                    }
                    writer.WriteLine("\nGame exit code: " + game.ExitCode);
                }
            }
            return 0;
        } catch (Exception error) {
            Console.Error.WriteLine("Debug capture failed: " + error.Message);
            Console.Error.WriteLine("Close other debug-output readers such as DebugView before retrying.");
            return 1;
        }
    }
}
