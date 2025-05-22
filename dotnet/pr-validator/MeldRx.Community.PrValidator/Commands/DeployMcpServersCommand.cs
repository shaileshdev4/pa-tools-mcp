using CommandLine;

namespace MeldRx.Community.PrValidator.Commands;

[Verb("deploy-mcp-servers", HelpText = "Deploys new MCP servers using dokploy.")]
public class DeployMcpServersCommand : ICommand
{
    [Option('n', "new-files", HelpText = "A list of files that have been newly created")]
    public IEnumerable<string> NewFiles { get; set; } = [];
}

public class DeployMcpServersCommandHandler : ICommandHandler<DeployMcpServersCommand>
{
    public Task<bool> HandleAsync(DeployMcpServersCommand command)
    {
        Console.WriteLine($"New files generated: {string.Join(" | ", command.NewFiles)}");
        return Task.FromResult(true);
    }
}
