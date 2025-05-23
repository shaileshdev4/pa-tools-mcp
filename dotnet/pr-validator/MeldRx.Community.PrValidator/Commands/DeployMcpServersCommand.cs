using System.Net.Http.Headers;
using System.Net.Mime;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using CommandLine;
using MeldRx.Community.PrValidator.Dokploy;

namespace MeldRx.Community.PrValidator.Commands;

[Verb("deploy-mcp-servers", HelpText = "Deploys new MCP servers using dokploy.")]
public class DeployMcpServersCommand : ICommand
{
    [Option('n', "new-files", HelpText = "A list of files that have been newly created")]
    public IEnumerable<string> NewFiles { get; set; } = [];
}

public class DeployMcpServersCommandHandler : ICommandHandler<DeployMcpServersCommand>
{
    private readonly HttpClient _httpClient = new HttpClient();
    private readonly JsonSerializerOptions _serializerOptions = new JsonSerializerOptions
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        Converters = { new JsonStringEnumConverter() },
    };

    public DeployMcpServersCommandHandler()
    {
        _httpClient.BaseAddress = new Uri(GetEnvVarOrThrow("DOKPLOY_API_URL"));
        _httpClient.DefaultRequestHeaders.Add("x-api-key", GetEnvVarOrThrow("DOKPLOY_API_KEY"));
    }

    public async Task<bool> HandleAsync(DeployMcpServersCommand command)
    {
        var newFiles = command
            .NewFiles.Where(x => x.EndsWith(".csproj", StringComparison.InvariantCultureIgnoreCase))
            .ToList();

        if (newFiles.Count == 0)
        {
            return true;
        }

        foreach (var file in newFiles)
        {
            var fi = new FileInfo(file);
            var directoryName =
                Path.GetDirectoryName(file)
                ?? throw new InvalidOperationException(
                    $"Could not determine directory of file: {file}"
                );

            var projectName = fi.Name.Replace(fi.Extension, string.Empty);
            var (name, longName) = GetNamesOfProject(projectName);

            var createAppResponse = await CreateApplicationAsync(name, longName);
            await SaveGitDetailsAsync(createAppResponse.ApplicationId, directoryName);
            await SaveDockerDetailsAsync(createAppResponse.ApplicationId, directoryName);
            await CreateDomainAsync(createAppResponse.ApplicationId, name);
        }

        return true;
    }

    private async Task<CreateApplicationResponse> CreateApplicationAsync(
        string name,
        string longName
    )
    {
        Console.WriteLine($"Creating application for: {name}");
        var projectId = GetEnvVarOrThrow("DOKPLOY_PROJECT_ID");
        var serverId = GetEnvVarOrThrow("DOKPLOY_SERVER_ID");

        var request = new CreateApplicationRequest
        {
            Name = name,
            AppName = longName,
            ProjectId = projectId,
            ServerId = serverId,
        };

        return await SendRequestAsync<CreateApplicationRequest, CreateApplicationResponse>(
            HttpMethod.Post,
            "application.create",
            request
        );
    }

    private async Task SaveGitDetailsAsync(string applicationId, string directoryName)
    {
        Console.WriteLine($"Updating GIT details for: {directoryName}");
        var githubUrl = GetEnvVarOrThrow("DOKPLOY_GITHUB_URL");
        var saveGitProviderRequest = new SaveGitProviderRequest
        {
            ApplicationId = applicationId,
            CustomGitUrl = githubUrl,
            CustomGitBranch = "main",
            CustomGitBuildPath = $"/{DirectoryNames.Dotnet}",
            WatchPaths = [$"{directoryName}/**"],
        };

        await SendRequestAsync(
            HttpMethod.Post,
            "application.saveGitProdiver",
            saveGitProviderRequest
        );
    }

    private async Task SaveDockerDetailsAsync(string applicationId, string directoryName)
    {
        Console.WriteLine($"Updating docker details for: {directoryName}");
        var saveBuildTypeRequest = new SaveBuildTypeRequest
        {
            ApplicationId = applicationId,
            Dockerfile =
                $"{directoryName.Replace($"{DirectoryNames.Dotnet}/", string.Empty)}/Dockerfile",
        };

        await SendRequestAsync(HttpMethod.Post, "application.saveBuildType", saveBuildTypeRequest);
    }

    private async Task CreateDomainAsync(string applicationId, string name)
    {
        Console.WriteLine($"Creating domain for: {name}");
        var subdomain = GetEnvVarOrThrow("DOKPLOY_SUBDOMAIN");
        var createDomainRequest = new CreateDomainRequest
        {
            ApplicationId = applicationId,
            Host = $"https://{name}.{subdomain}",
            Port = 5000,
            Https = true,
        };

        await SendRequestAsync(HttpMethod.Post, "domain.create", createDomainRequest);
    }

    private async Task<HttpResponseMessage> SendRequestAsync<T>(
        HttpMethod verb,
        string path,
        T? data = default
    )
    {
        var request = new HttpRequestMessage(verb, path);
        if (data is not null)
        {
            request.Content = new StringContent(
                JsonSerializer.Serialize(data, _serializerOptions),
                new MediaTypeHeaderValue(MediaTypeNames.Application.Json)
            );
        }

        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();

        return response;
    }

    private async Task<TResponse> SendRequestAsync<T, TResponse>(
        HttpMethod verb,
        string path,
        T? data = default
    )
    {
        var response = await SendRequestAsync(verb, path, data);
        var body = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<TResponse>(body, _serializerOptions)
            ?? throw new InvalidOperationException(
                $"Could not deserialize to type: {typeof(TResponse).Name}"
            );
    }

    private (string name, string longName) GetNamesOfProject(string projectName)
    {
        var identifier = projectName[(projectName.LastIndexOf('.') + 1)..];
        var kebabCaseBuilder = new StringBuilder();
        for (var i = 0; i < identifier.Length; i++)
        {
            var c = identifier[i];
            if (char.IsUpper(c) && i != 0)
            {
                kebabCaseBuilder.Append('-');
            }

            kebabCaseBuilder.Append(char.ToLowerInvariant(c));
        }

        var name = kebabCaseBuilder.ToString();
        return (name, $"mcp-servers-{name}");
    }

    private string GetEnvVarOrThrow(string envName)
    {
        return Environment.GetEnvironmentVariable(envName)
            ?? throw new InvalidOperationException(
                $"Required environment variable not found: {envName}"
            );
    }
}
