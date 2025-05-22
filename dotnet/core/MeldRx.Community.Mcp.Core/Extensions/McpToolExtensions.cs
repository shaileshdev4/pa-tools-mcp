using ModelContextProtocol.Protocol;

namespace MeldRx.Community.Mcp.Core.Extensions;

public static class McpToolExtensions
{
    public static string? GetArgumentValueOrNull(
        this CallToolRequestParams context,
        string parameterName
    )
    {
        ArgumentNullException.ThrowIfNull(context.Arguments);

        return context.Arguments.TryGetValue(parameterName, out var element)
            ? element.GetString()
            : null;
    }

    public static string GetRequiredArgumentValue(
        this CallToolRequestParams context,
        string parameterName
    )
    {
        ArgumentNullException.ThrowIfNull(context.Arguments);

        var value = GetArgumentValueOrNull(context, parameterName);
        if (string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException(
                $"The following parameter is required: {parameterName}"
            );
        }

        return value;
    }
}
