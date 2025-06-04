namespace DarenaHealth.Community.Mcp.Core.Models;

public class McpToolArgument
{
    public required string Name { get; set; }

    public required string Type { get; set; }

    public bool IsRequired { get; set; }

    public string? Description { get; set; }
}
