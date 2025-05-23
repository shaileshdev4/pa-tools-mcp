namespace MeldRx.Community.PrValidator.Dokploy;

public class CreateApplicationRequest
{
    public required string Name { get; set; }

    public required string ProjectId { get; set; }

    public required string ServerId { get; set; }

    public string? AppName { get; set; }
}
