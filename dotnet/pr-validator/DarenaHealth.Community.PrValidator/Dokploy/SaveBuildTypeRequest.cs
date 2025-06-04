namespace DarenaHealth.Community.PrValidator.Dokploy;

public class SaveBuildTypeRequest
{
    public required string ApplicationId { get; set; }

    public string BuildType { get; } = "dockerfile";

    public string DockerContextPath { get; set; } = $"/{DirectoryNames.Dotnet}";

    public string DockerBuildStage { get; set; } = string.Empty;

    public string? Dockerfile { get; set; }
}
