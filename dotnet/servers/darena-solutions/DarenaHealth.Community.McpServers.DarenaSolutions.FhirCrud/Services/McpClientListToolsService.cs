using System.Text.Json;
using System.Text.Json.Nodes;
using DarenaHealth.Community.Mcp.Core;
using DarenaHealth.Community.Mcp.Core.Models;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace DarenaHealth.Community.McpServers.DarenaSolutions.FhirCrud.Services;

public static class McpClientListToolsService
{
    public static ValueTask<ListToolsResult> Handler(
        RequestContext<ListToolsRequestParams> context,
        CancellationToken cancellation
    )
    {
        ArgumentNullException.ThrowIfNull(context.Services);

        var tools = context.Services.GetRequiredService<IEnumerable<IMcpTool>>();
        var responseTools = tools
            .Select(x => new Tool
            {
                Name = x.Name,
                Description = x.Description,
                InputSchema = ToInputSchema(x.Arguments),
            })
            .ToList();

        return ValueTask.FromResult(new ListToolsResult { Tools = responseTools });
    }

    private static JsonElement ToInputSchema(List<McpToolArgument> arguments)
    {
        var requiredProps = new List<string>();
        var propertiesObj = new JsonObject();

        foreach (var argument in arguments)
        {
            if (argument.IsRequired)
            {
                requiredProps.Add(argument.Name);
            }

            var typeObj = new JsonObject { ["type"] = argument.Type };
            if (!string.IsNullOrWhiteSpace(argument.Description))
            {
                typeObj.Add("description", argument.Description);
            }

            propertiesObj.Add(argument.Name, typeObj);
        }

        var schema = new JsonObject { ["type"] = "object", ["properties"] = propertiesObj };
        if (requiredProps.Count > 0)
        {
            schema.Add("required", new JsonArray([.. requiredProps]));
        }

        return JsonSerializer.SerializeToElement(schema);
    }
}
