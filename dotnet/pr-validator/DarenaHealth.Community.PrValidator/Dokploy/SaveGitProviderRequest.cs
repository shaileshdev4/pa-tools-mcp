namespace DarenaHealth.Community.PrValidator.Dokploy;

public class SaveGitProviderRequest
{
    public required string ApplicationId { get; set; }

    public string? CustomGitBranch { get; set; }

    public string? CustomGitBuildPath { get; set; }

    public string? CustomGitUrl { get; set; }

    public List<string> WatchPaths { get; set; } = [];
}
