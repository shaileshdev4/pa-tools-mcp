using System.Net.Http.Headers;
using System.Net.Mime;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using CommandLine;
using MeldRx.Community.PrValidator.Dokploy;

namespace MeldRx.Community.PrValidator.Commands;

[Verb("deploy-mcp-servers", HelpText = "Deploys new MCP servers using dokploy.")]
public class DeployMcpServersCommand : ICommand
{
    [Option('c', "changed-files", HelpText = "A list of files that were changed")]
    public IEnumerable<string> ChangedFiles { get; set; } = [];
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
        var changedFiles = command.ChangedFiles.ToList();
        if (changedFiles.Count == 0)
        {
            Console.WriteLine("No files were changed. Skipping.");
            return true;
        }

        if (!FileUtilities.TryGetProjectDirectories(changedFiles, out var projectDirectories))
        {
            return false;
        }

        if (projectDirectories.Count == 0)
        {
            Console.WriteLine("No project directories were found. Skipping.");
            return true;
        }

        var projectId = GetEnvVarOrThrow("DOKPLOY_PROJECT_ID");
        foreach (var directory in projectDirectories)
        {
            var language = directory.Contains(
                $"{DirectoryNames.Dotnet}{Path.DirectorySeparatorChar}"
            )
                ? ProgrammingLanguage.Net
                : ProgrammingLanguage.Typescript;

            var (name, longName) = GetNamesOfProject(directory);
            var applicationId = await GetApplicationIdIfExistsOrNullAsync(name, projectId);

            if (string.IsNullOrWhiteSpace(applicationId))
            {
                var createAppResponse = await CreateApplicationAsync(name, longName, projectId);
                await SaveGitDetailsAsync(language, createAppResponse.ApplicationId, directory);
                await SaveDockerDetailsAsync(language, createAppResponse.ApplicationId, directory);
                await CreateDomainAsync(createAppResponse.ApplicationId, name);
                await DeployApplicationAsync(createAppResponse.ApplicationId, isNew: true);
            }
            else
            {
                await DeployApplicationAsync(applicationId, isNew: false);
            }
        }

        return true;
    }

    private async Task<string?> GetApplicationIdIfExistsOrNullAsync(string name, string projectId)
    {
        var response = await SendRequestAsync<object, GetProjectResponse>(
            HttpMethod.Get,
            $"project.one?projectId={projectId}"
        );

        var existing = response.Applications.FirstOrDefault(x => x.Name == name);
        return existing?.ApplicationId;
    }

    private async Task<CreateApplicationResponse> CreateApplicationAsync(
        string name,
        string longName,
        string projectId
    )
    {
        Console.WriteLine($"Creating application for: {name}");
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

    private async Task SaveGitDetailsAsync(
        ProgrammingLanguage language,
        string applicationId,
        string directoryName
    )
    {
        Console.WriteLine($"Updating GIT details for: {directoryName}");
        var githubUrl = GetEnvVarOrThrow("DOKPLOY_GITHUB_URL");
        var saveGitProviderRequest = new SaveGitProviderRequest
        {
            ApplicationId = applicationId,
            CustomGitUrl = githubUrl,
            CustomGitBranch = "main",
            CustomGitBuildPath =
                language == ProgrammingLanguage.Net
                    ? $"/{DirectoryNames.Dotnet}"
                    : $"/{DirectoryNames.Typescript}",
            WatchPaths = [$"{directoryName}/**"],
        };

        await SendRequestAsync(
            HttpMethod.Post,
            "application.saveGitProdiver",
            saveGitProviderRequest
        );
    }

    private async Task SaveDockerDetailsAsync(
        ProgrammingLanguage language,
        string applicationId,
        string directoryName
    )
    {
        Console.WriteLine($"Updating docker details for: {directoryName}");

        directoryName =
            language == ProgrammingLanguage.Net
                ? directoryName.Replace($"{DirectoryNames.Dotnet}/", string.Empty)
                : directoryName.Replace($"{DirectoryNames.Typescript}/", string.Empty);

        var saveBuildTypeRequest = new SaveBuildTypeRequest
        {
            ApplicationId = applicationId,
            Dockerfile = $"{directoryName}/Dockerfile",
        };

        await SendRequestAsync(HttpMethod.Post, "application.saveBuildType", saveBuildTypeRequest);
    }

    private async Task CreateDomainAsync(string applicationId, string name)
    {
        var randomizedName =
            $"{name}{RandomNumberGenerator.GetString("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 6)}";

        Console.WriteLine($"Creating domain for: {randomizedName}");
        var subdomain = GetEnvVarOrThrow("DOKPLOY_SUBDOMAIN");
        var createDomainRequest = new CreateDomainRequest
        {
            ApplicationId = applicationId,
            Host = $"https://{randomizedName}.{subdomain}",
            Port = 5000,
            Https = true,
        };

        Console.WriteLine($"Successfully created domain: {randomizedName}");
        await SendRequestAsync(HttpMethod.Post, "domain.create", createDomainRequest);
    }

    private async Task DeployApplicationAsync(string applicationId, bool isNew)
    {
        var url = isNew ? "application.deploy" : "application.redeploy";
        var response = await SendRequestAsync(
            HttpMethod.Post,
            url,
            new DeployApplicationRequest { ApplicationId = applicationId }
        );

        response.EnsureSuccessStatusCode();
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

    private (string name, string longName) GetNamesOfProject(string directory)
    {
        var directoryIndex = directory.LastIndexOf('.');
        if (directoryIndex < 0)
        {
            directoryIndex = directory.LastIndexOf(Path.DirectorySeparatorChar);
        }

        var identifier = directory[(directoryIndex + 1)..];
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
