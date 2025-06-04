using DarenaHealth.Community.Mcp.Core;
using DarenaHealth.Community.Mcp.Core.Extensions;
using DarenaHealth.Community.Mcp.Core.Models;
using Hl7.Fhir.Model;
using Hl7.Fhir.Rest;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace DarenaHealth.Community.McpServers.DarenaSolutions.FhirCrud.Tools;

public class FindPatientIdTool : IMcpTool
{
    private const string FirstNameParameter = "firstName";
    private const string LastNameParameter = "lastName";

    public string Name { get; } = "find_patient_id";

    public string? Description { get; } =
        "Finds an id of the patient. It is not required to supply both first name and last name, only one of the parameters "
        + "is sufficient. If patient context already exists, then do not supply first name and last name unless the user "
        + "explicitly provides this information.";

    public List<McpToolArgument> Arguments { get; } =
        [
            new McpToolArgument
            {
                Type = "string",
                Name = FirstNameParameter,
                Description = "The patient's first name",
                IsRequired = false,
            },
            new McpToolArgument
            {
                Type = "string",
                Name = LastNameParameter,
                Description = "The patient's last name",
                IsRequired = false,
            },
        ];

    public List<string> FhirScopes { get; } = ["patient/Patient.read"];

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

        var patientIdContext = httpContext.GetPatientIdIfContextExists();
        if (!string.IsNullOrWhiteSpace(patientIdContext))
        {
            return McpToolUtilities.CreateTextToolResponse(patientIdContext);
        }

        if (context.Arguments is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "No patient context found, thus the first name or last name is required.",
                isError: true
            );
        }

        var firstName = context.GetArgumentValueOrNull(FirstNameParameter);
        var lastName = context.GetArgumentValueOrNull(LastNameParameter);

        if (string.IsNullOrWhiteSpace(firstName) && string.IsNullOrWhiteSpace(lastName))
        {
            return McpToolUtilities.CreateTextToolResponse(
                "No patient context found, thus the first name or last name is required.",
                isError: true
            );
        }

        var fhirSettings = new FhirClientSettings { PreferredFormat = ResourceFormat.Json };
        var fhirClient = new FhirClient(
            fhirContext.Url,
            fhirSettings,
            new FhirClientAuthMessageHandler(fhirContext.Token)
        );

        var searchParams = new SearchParams();
        if (!string.IsNullOrWhiteSpace(firstName))
        {
            searchParams.Where($"given={firstName}");
        }

        if (!string.IsNullOrWhiteSpace(lastName))
        {
            searchParams.Where($"family={lastName}");
        }

        try
        {
            var response = await fhirClient.SearchAsync<Patient>(searchParams);
            if (response?.Entry is not { Count: > 0 })
            {
                searchParams = new SearchParams();
                if (!string.IsNullOrWhiteSpace(lastName))
                {
                    searchParams.Where($"given={lastName}");
                }

                if (!string.IsNullOrWhiteSpace(firstName))
                {
                    searchParams.Where($"family={firstName}");
                }

                response = await fhirClient.SearchAsync<Patient>(searchParams);
                if (response?.Entry is not { Count: > 0 })
                {
                    return McpToolUtilities.CreateTextToolResponse(
                        "The patient could not be found.",
                        isError: true
                    );
                }
            }

            if (response.Entry.Count > 1)
            {
                return McpToolUtilities.CreateTextToolResponse(
                    "More than one patient found. Need more details",
                    isError: true
                );
            }

            return McpToolUtilities.CreateTextToolResponse(response.Entry[0].Resource.Id);
        }
        catch (Exception e)
        {
            return McpToolUtilities.CreateTextToolResponse(
                $"An exception occurred with message: {e.Message}",
                isError: true
            );
        }
    }
}
