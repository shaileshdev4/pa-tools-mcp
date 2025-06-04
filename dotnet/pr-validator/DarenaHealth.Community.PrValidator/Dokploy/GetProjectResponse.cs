namespace DarenaHealth.Community.PrValidator.Dokploy;

public class GetProjectResponse
{
    public required string ProjectId { get; set; }

    public List<GetProjectResponseApplication> Applications { get; set; } = [];
}

public class GetProjectResponseApplication
{
    public required string ApplicationId { get; set; }

    public required string Name { get; set; }

    public required string AppName { get; set; }
}
