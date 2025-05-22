using System.Diagnostics;
using System.Text;

namespace MeldRx.Community.PrValidator;

public class ProcessHelper : IDisposable
{
    private bool _disposed;
    private readonly Process _process;

    public ProcessHelper(string name, string arguments, string? workingDirectory = null)
    {
        _process = new Process
        {
            StartInfo =
            {
                FileName = name,
                Arguments = arguments,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
            },
        };

        if (!string.IsNullOrWhiteSpace(workingDirectory))
        {
            _process.StartInfo.WorkingDirectory = workingDirectory;
        }
    }

    public async Task RunAsync()
    {
        _process.StartInfo.RedirectStandardOutput = false;
        _process.StartInfo.RedirectStandardError = false;

        _process.Start();
        await _process.WaitForExitAsync();

        if (_process.ExitCode != 0)
        {
            throw new ProcessHelperException(
                $"Internal process terminated with exit code: {_process.ExitCode}"
            );
        }
    }

    public async Task<string> GetOutputAsync()
    {
        var builder = new StringBuilder();
        var errorBuilder = new StringBuilder();
        _process.OutputDataReceived += (sender, args) =>
        {
            if (string.IsNullOrWhiteSpace(args.Data))
            {
                return;
            }

            builder.AppendLine(args.Data);
        };

        _process.ErrorDataReceived += (sender, args) =>
        {
            if (string.IsNullOrWhiteSpace(args.Data))
            {
                return;
            }

            errorBuilder.AppendLine(args.Data);
        };

        _process.Start();
        _process.BeginOutputReadLine();
        _process.BeginErrorReadLine();

        await _process.WaitForExitAsync();

        var error = errorBuilder.ToString();
        if (!string.IsNullOrWhiteSpace(error))
        {
            throw new ProcessHelperException(error);
        }

        return builder.ToString();
    }

    public void Dispose()
    {
        Dispose(disposing: true);
        GC.SuppressFinalize(this);
    }

    protected virtual void Dispose(bool disposing)
    {
        if (_disposed)
        {
            return;
        }

        if (disposing)
        {
            _process.Dispose();
        }

        _disposed = true;
    }
}
