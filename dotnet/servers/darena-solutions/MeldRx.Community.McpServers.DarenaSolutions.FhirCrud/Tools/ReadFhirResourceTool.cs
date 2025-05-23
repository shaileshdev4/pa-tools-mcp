using Hl7.Fhir.Rest;
using Hl7.Fhir.Serialization;
using MeldRx.Community.Mcp.Core;
using MeldRx.Community.Mcp.Core.Extensions;
using MeldRx.Community.Mcp.Core.Models;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Tools;

public class ReadFhirResourceTool : IMcpTool
{
    private const string ResourceTypeParameter = "resourceType";
    private const string ResourceIdParameter = "resourceId";

    public string Name { get; } = "read_fhir_resource";

    public string? Description { get; } =
        "Reads a FHIR resource from a FHIR server given a resource type and resource id. This can be used to obtain "
        + "additional details of a resource.";

    public List<McpToolArgument> Arguments { get; } =
        [
            new McpToolArgument
            {
                Type = "string",
                Name = ResourceTypeParameter,
                Description = "The FHIR resource type. (EG: Patient, Encounter, Observation, etc.)",
                IsRequired = true,
            },
            new McpToolArgument
            {
                Type = "string",
                Name = ResourceIdParameter,
                Description =
                    "The ID of the resource to retrieve. This should be a guid. If it is not a guid or there is no resource id, "
                    + "use another tool to first find the resource id",
                IsRequired = true,
            },
        ];

    public List<string> FhirScopes { get; } = ["patient/*.read"];

    public async Task<CallToolResponse> HandleAsync(
        HttpContext httpContext,
        IMcpServer mcpServer,
        CallToolRequestParams context
    )
    {
        var fhirContext = httpContext.GetFhirContext();
        if (fhirContext is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "A FHIR server url or token was not provided in the http context.",
                isError: true
            );
        }

        var resourceType = context.GetRequiredArgumentValue(ResourceTypeParameter);
        var resourceId = context.GetRequiredArgumentValue(ResourceIdParameter);

        var fhirSettings = new FhirClientSettings { PreferredFormat = ResourceFormat.Json };
        var fhirClient = new FhirClient(
            fhirContext.Url,
            fhirSettings,
            new FhirClientAuthMessageHandler(fhirContext.Token)
        );

        var response = await fhirClient.GetAsync($"{resourceType}/{resourceId}");
        if (response is null)
        {
            return McpToolUtilities.CreateTextToolResponse("The patient could not be found.");
        }

        var serializer = new FhirJsonSerializer();
        var json = await serializer.SerializeToStringAsync(response);

        return McpToolUtilities.CreateTextToolResponse(json);
    }
}
