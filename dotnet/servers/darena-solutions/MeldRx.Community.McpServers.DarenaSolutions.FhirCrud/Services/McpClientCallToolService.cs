using MeldRx.Community.Mcp.Core;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Services;

public static class McpClientCallToolService
{
    public static async ValueTask<CallToolResponse> Handler(
        RequestContext<CallToolRequestParams> context,
        CancellationToken cancellation
    )
    {
        if (context.Services is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "An unexpected server error occurred. Services were not found.",
                isError: true
            );
        }

        if (context.Params is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "An unexpected server error occurred. No tool parameters found.",
                isError: true
            );
        }

        var tools = context.Services.GetRequiredService<IEnumerable<IMcpTool>>();
        var contextAccessor = context.Services.GetRequiredService<IHttpContextAccessor>();

        if (contextAccessor.HttpContext is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "An unexpected server error occurred. The HTTP context could not be determined.",
                isError: true
            );
        }

        foreach (var tool in tools)
        {
            if (tool.Name != context.Params.Name)
            {
                continue;
            }

            try
            {
                return await tool.HandleAsync(
                    contextAccessor.HttpContext,
                    context.Server,
                    context.Params
                );
            }
            catch (Exception exception)
            {
                return McpToolUtilities.CreateTextToolResponse(
                    $"An internal exception occurred with message: {exception.Message}",
                    isError: true
                );
            }
        }

        return McpToolUtilities.CreateTextToolResponse(
            $"A tool handler was not found for the tool: {context.Params.Name}.",
            isError: true
        );
    }
}
