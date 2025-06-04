using DarenaHealth.Community.Mcp.Core.Models;
using Microsoft.AspNetCore.Http;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace DarenaHealth.Community.Mcp.Core;

public interface IMcpTool
{
    string Name { get; }

    string? Description { get; }

    List<McpToolArgument> Arguments { get; }

    List<string> FhirScopes { get; }

    Task<CallToolResponse> HandleAsync(
        HttpContext httpContext,
        IMcpServer mcpServer,
        CallToolRequestParams context
    );
}
