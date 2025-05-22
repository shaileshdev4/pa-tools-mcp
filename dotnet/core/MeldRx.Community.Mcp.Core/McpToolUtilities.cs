using ModelContextProtocol.Protocol;

namespace MeldRx.Community.Mcp.Core;

public static class McpToolUtilities
{
    public static CallToolResponse CreateTextToolResponse(string text, bool isError = false)
    {
        return new CallToolResponse
        {
            Content = [new Content { Type = "text", Text = text }],
            IsError = isError,
        };
    }
}
