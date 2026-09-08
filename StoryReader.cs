using System;
using System.IO;
using System.Net;
using System.Diagnostics;
using System.Threading;

namespace StoryCrafterLauncher
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.Title = "StoryCrafter Reader - One Click Setup & Launcher";
            Console.ForegroundColor = ConsoleColor.Cyan;
            Console.WriteLine("==========================================================");
            Console.WriteLine("       StoryCrafter Sleek Desktop Book Reader             ");
            Console.WriteLine("==========================================================");
            Console.ResetColor();
            Console.WriteLine();

            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            Directory.SetCurrentDirectory(appDir);

            // Step 1: Ensure .gitignore ignores .venv
            EnsureGitIgnore(appDir);

            // Step 2: Locate or install Python
            string pythonExe = FindOrInstallPython();
            if (string.IsNullOrEmpty(pythonExe))
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("\n[ERROR] Unable to locate or install Python. Please install Python manually from python.org.");
                Console.ResetColor();
                Console.WriteLine("\nPress any key to exit...");
                Console.ReadKey();
                return;
            }

            // Step 3: Create .venv if not present
            string venvPython = Path.Combine(appDir, ".venv", "Scripts", "python.exe");
            string venvPythonw = Path.Combine(appDir, ".venv", "Scripts", "pythonw.exe");

            if (!File.Exists(venvPython))
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("[SETUP] Creating virtual environment (.venv)...");
                Console.ResetColor();

                int venvExit = RunProcess(pythonExe, "-m venv .venv");
                if (venvExit != 0 || !File.Exists(venvPython))
                {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine("[ERROR] Failed to create virtual environment.");
                    Console.ResetColor();
                    Console.WriteLine("\nPress any key to exit...");
                    Console.ReadKey();
                    return;
                }
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("[OK] Virtual environment created successfully.");
                Console.ResetColor();
            }

            // Step 4: Install/Verify requirements
            string reqFile = Path.Combine(appDir, "requirements.txt");
            if (File.Exists(reqFile))
            {
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("[SETUP] Checking and installing requirements...");
                Console.ResetColor();

                RunProcess(venvPython, "-m pip install -q -r requirements.txt");
            }

            // Step 5: Launch Reader App
            string readerApp = Path.Combine(appDir, "reader_app.py");
            if (File.Exists(readerApp))
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("[LAUNCH] Starting StoryCrafter Desktop Reader...\n");
                Console.ResetColor();

                string launcherExe = File.Exists(venvPythonw) ? venvPythonw : venvPython;
                ProcessStartInfo startInfo = new ProcessStartInfo
                {
                    FileName = launcherExe,
                    Arguments = "\"" + readerApp + "\"",
                    UseShellExecute = false,
                    WorkingDirectory = appDir
                };

                Process.Start(startInfo);
                Thread.Sleep(1500);
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("[ERROR] reader_app.py not found at: " + readerApp);
                Console.ResetColor();
                Console.WriteLine("\nPress any key to exit...");
                Console.ReadKey();
            }
        }

        static void EnsureGitIgnore(string appDir)
        {
            try
            {
                string gitignorePath = Path.Combine(appDir, ".gitignore");
                string defaultEntries = ".venv/\nvenv/\n__pycache__/\n*.py[cod]\n.reader_config.json\n";

                if (!File.Exists(gitignorePath))
                {
                    File.WriteAllText(gitignorePath, defaultEntries);
                    Console.WriteLine("[GIT] Created .gitignore with .venv excluded.");
                }
                else
                {
                    string content = File.ReadAllText(gitignorePath);
                    bool modified = false;
                    if (!content.Contains(".venv"))
                    {
                        content += "\n.venv/\n";
                        modified = true;
                    }
                    if (!content.Contains("venv"))
                    {
                        content += "venv/\n";
                        modified = true;
                    }
                    if (modified)
                    {
                        File.WriteAllText(gitignorePath, content);
                        Console.WriteLine("[GIT] Updated .gitignore to exclude .venv.");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("[WARN] Could not update .gitignore: " + ex.Message);
            }
        }

        static string FindOrInstallPython()
        {
            // Check PATH for python
            string pathPython = CheckCommand("python");
            if (!string.IsNullOrEmpty(pathPython))
            {
                Console.WriteLine("[DETECTED] System Python found: " + pathPython);
                return pathPython;
            }

            // Check py launcher
            string pyLauncher = CheckCommand("py");
            if (!string.IsNullOrEmpty(pyLauncher))
            {
                Console.WriteLine("[DETECTED] Python Launcher found: " + pyLauncher);
                return pyLauncher;
            }

            // Check standard Windows directories
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string pyDir = Path.Combine(localAppData, "Programs", "Python");
            if (Directory.Exists(pyDir))
            {
                foreach (string d in Directory.GetDirectories(pyDir, "Python3*"))
                {
                    string candidate = Path.Combine(d, "python.exe");
                    if (File.Exists(candidate))
                    {
                        Console.WriteLine("[DETECTED] Python found at: " + candidate);
                        return candidate;
                    }
                }
            }

            // Python not found: Attempt automatic installation
            Console.ForegroundColor = ConsoleColor.Yellow;
            Console.WriteLine("[INFO] Python was not detected on your system.");
            Console.WriteLine("[INSTALL] Attempting automatic silent installation of Python...");
            Console.ResetColor();

            // Try winget first if available
            string winget = CheckCommand("winget");
            if (!string.IsNullOrEmpty(winget))
            {
                Console.WriteLine("[WINGET] Installing Python 3.12 via Windows Package Manager...");
                int wingetExit = RunProcess("winget", "install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements");
                if (wingetExit == 0)
                {
                    string refreshed = CheckCommand("python");
                    if (!string.IsNullOrEmpty(refreshed)) return refreshed;
                }
            }

            // Direct download fallback
            try
            {
                string installerUrl = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe";
                string installerPath = Path.Combine(Path.GetTempPath(), "python_setup.exe");

                Console.WriteLine("[DOWNLOAD] Downloading official Python 3.12 installer...");
                using (WebClient client = new WebClient())
                {
                    client.DownloadFile(installerUrl, installerPath);
                }

                Console.WriteLine("[INSTALL] Running silent Python installation (please wait)...");
                int installExit = RunProcess(installerPath, "/quiet InstallAllUsers=0 PrependPath=1 SimpleInstall=1");

                if (File.Exists(installerPath))
                {
                    try { File.Delete(installerPath); } catch { }
                }

                // Refresh environment PATH
                string newPath = Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.User) + ";" +
                                 Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Machine);
                Environment.SetEnvironmentVariable("PATH", newPath);

                string installed = CheckCommand("python");
                if (!string.IsNullOrEmpty(installed)) return installed;
            }
            catch (Exception ex)
            {
                Console.WriteLine("[ERROR] Automatic Python installation failed: " + ex.Message);
            }

            return null;
        }

        static string CheckCommand(string cmd)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = cmd,
                    Arguments = "--version",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using (Process p = Process.Start(psi))
                {
                    p.WaitForExit(3000);
                    if (p.ExitCode == 0)
                    {
                        return cmd;
                    }
                }
            }
            catch { }
            return null;
        }

        static int RunProcess(string filename, string args)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = filename,
                    Arguments = args,
                    UseShellExecute = false,
                    CreateNoWindow = false
                };

                using (Process p = Process.Start(psi))
                {
                    p.WaitForExit();
                    return p.ExitCode;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("[ERROR] Process execution failed: " + ex.Message);
                return -1;
            }
        }
    }
}
