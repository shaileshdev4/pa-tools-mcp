using CommandLine;
using ModelContextProtocol.Client;

namespace MeldRx.Community.PrValidator.Commands;

[Verb("verify-list-tools", HelpText = "Verifies that an MCP server can list tools.")]
public class VerifyListToolsCommand : ICommand
{
    [Option('c', "changed-files", HelpText = "A list of files that were changed")]
    public IEnumerable<string> ChangedFiles { get; set; } = [];
}

public class VerifyListToolsCommandHandler : ICommandHandler<VerifyListToolsCommand>
{
    private const string McpServerEndpoint = "http://localhost:3056";
    private readonly HttpClient _httpClient = new HttpClient();

    public async Task<bool> HandleAsync(VerifyListToolsCommand command)
    {
        if (!TryGetProjectDirectories(command, out var projectDirectories))
        {
            return false;
        }

        foreach (var projectDir in projectDirectories)
        {
            Console.WriteLine($"Building and testing project directory: {projectDir}");

            try
            {
                using (
                    var buildProcess = new ProcessHelper(
                        "dotnet",
                        "publish -c Release -r linux-x64 -o publish",
                        workingDirectory: projectDir
                    )
                )
                {
                    await buildProcess.RunAsync();
                }

                using (
                    var dockerBuildProcess = new ProcessHelper(
                        "docker",
                        "build -t mcpserver .",
                        workingDirectory: projectDir
                    )
                )
                {
                    await dockerBuildProcess.RunAsync();
                }

                using var dockerRunProcess = new ProcessHelper(
                    "docker",
                    "run --name TestMcpServer -d -p 3056:5000 mcpserver:latest",
                    workingDirectory: projectDir
                );

                await dockerRunProcess.RunAsync();
                if (!await TryWaitUntilServerIsReadyAsync(projectDir))
                {
                    return false;
                }

                await using var mcpClient = await CreateClientAsync();
                var tools = await mcpClient.ListToolsAsync();
                if (tools.Count == 0)
                {
                    ConsoleUtilities.WriteErrorLine(
                        $"ERROR: No tools were returned by the MCP server at project location: {projectDir}"
                    );

                    return false;
                }

                var toolNames = tools.Select(x => x.Name).ToList();
                Console.WriteLine(
                    $"SUCCESS: Tools returned: {string.Join(" | ", toolNames)}. Project: {projectDir}"
                );
            }
            catch (ProcessHelperException exception)
            {
                ConsoleUtilities.WriteErrorLine(exception.Message);
                return false;
            }
        }

        return true;
    }

    private async Task<IMcpClient> CreateClientAsync()
    {
        var transportOptions = new SseClientTransportOptions
        {
            Endpoint = new Uri(McpServerEndpoint),
            UseStreamableHttp = true,
        };

        var clientTransport = new SseClientTransport(transportOptions);
        return await McpClientFactory.CreateAsync(clientTransport);
    }

    private async Task<bool> TryWaitUntilServerIsReadyAsync(string projectDir)
    {
        var retries = 0;

        while (true)
        {
            try
            {
                var url = $"{McpServerEndpoint}/hello-world";
                var response = await _httpClient.GetAsync(url);

                response.EnsureSuccessStatusCode();
                return true;
            }
            catch
            {
                retries++;
                if (retries == 3)
                {
                    ConsoleUtilities.WriteErrorLine(
                        $"Attempted /hello-world 3 times without success for project: {projectDir}"
                    );

                    return false;
                }

                await Task.Delay(1500);
            }
        }
    }

    private bool TryGetProjectDirectories(
        VerifyListToolsCommand command,
        out List<string> projectDirectories
    )
    {
        projectDirectories = [];
        var directoriesChecked = new HashSet<string>();
        var rootDirectory = FileUtilities.GetRepoRootDirectory();

        foreach (var file in command.ChangedFiles)
        {
            var fi = new FileInfo(Path.Combine(rootDirectory, file));
            if (fi.Directory is null)
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: The following file is not contained in a directory: {file}"
                );

                return false;
            }

            if (!directoriesChecked.Add(fi.Directory.FullName))
            {
                continue;
            }

            if (
                !TryFindProjectDirectory(fi.Directory, file, out var projectDi) || projectDi is null
            )
            {
                return false;
            }

            projectDirectories.Add(projectDi.FullName);
            directoriesChecked.Add(projectDi.FullName);
        }

        return true;
    }

    private bool TryFindProjectDirectory(
        DirectoryInfo di,
        string startFile,
        out DirectoryInfo? projectDi
    )
    {
        projectDi = null;
        while (true)
        {
            string? projectFile = null;
            string? dockerFile = null;
            foreach (var fi in di.EnumerateFiles())
            {
                if (
                    string.Equals(
                        ".csproj",
                        fi.Extension,
                        StringComparison.InvariantCultureIgnoreCase
                    )
                )
                {
                    projectFile = fi.FullName;
                }

                if (
                    string.Equals(
                        "dockerfile",
                        fi.Name,
                        StringComparison.InvariantCultureIgnoreCase
                    )
                )
                {
                    dockerFile = fi.FullName;
                }
            }

            if (string.IsNullOrWhiteSpace(projectFile))
            {
                if (di.Parent is null)
                {
                    ConsoleUtilities.WriteErrorLine(
                        $"ERROR: Could not find the project directory for file: {startFile}"
                    );

                    return false;
                }

                di = di.Parent;
                continue;
            }

            if (string.IsNullOrWhiteSpace(dockerFile))
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: Could not find docker file in project directory: {di.FullName}"
                );

                return false;
            }

            projectDi = di;
            return true;
        }
    }
}
