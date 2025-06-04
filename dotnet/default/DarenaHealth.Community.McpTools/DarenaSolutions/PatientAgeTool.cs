using DarenaHealth.Community.Mcp.Core;
using DarenaHealth.Community.Mcp.Core.Extensions;
using DarenaHealth.Community.Mcp.Core.Models;
using Hl7.Fhir.Model;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using ModelContextProtocol.Protocol;
using ModelContextProtocol.Server;

namespace DarenaHealth.Community.McpTools.DarenaSolutions;

public class PatientAgeTool : IMcpTool
{
    private const string FirstNameParameter = "firstName";
    private const string LastNameParameter = "lastName";

    public string Name { get; } = "GetPatientAge";

    public string? Description { get; } =
        "Gets the age of a patient. If patient context already exists, then the first name and last name is not required.";

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

        if (mcpServer.Services is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "An unexpected server error occurred. Services were not found.",
                isError: true
            );
        }

        var searchService = mcpServer.Services.GetRequiredService<IPatientSearchService>();

        Patient? patient = null;
        var patientIdContext = httpContext.GetPatientIdIfContextExists();
        if (!string.IsNullOrWhiteSpace(patientIdContext))
        {
            patient = await searchService.FindByIdAsync(fhirContext, patientIdContext);
        }
        else
        {
            if (context.Arguments is null)
            {
                return McpToolUtilities.CreateTextToolResponse(
                    "No arguments were specified",
                    isError: true
                );
            }

            var firstName = context.GetArgumentValueOrNull(FirstNameParameter);
            var lastName = context.GetArgumentValueOrNull(LastNameParameter);

            if (string.IsNullOrWhiteSpace(firstName) && string.IsNullOrWhiteSpace(lastName))
            {
                return McpToolUtilities.CreateTextToolResponse(
                    "Patient context was not found, thus the first name, last name, or both is required.",
                    isError: true
                );
            }

            var patients = await searchService.SearchByNameAsync(fhirContext, firstName, lastName);
            if (patients.Count == 0)
            {
                patients = await searchService.SearchByNameAsync(fhirContext, lastName, firstName);
            }

            if (patients.Count > 1)
            {
                return McpToolUtilities.CreateTextToolResponse(
                    "More than one patient found. Provide additional details.",
                    isError: true
                );
            }

            if (patients.Count == 1)
            {
                patient = patients[0];
            }
        }

        if (patient is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "The patient could not be found.",
                isError: true
            );
        }

        var patientDob = patient.BirthDateElement?.ToDate()?.ToDateTime();
        if (patientDob?.Years is null)
        {
            return McpToolUtilities.CreateTextToolResponse(
                "This patient does not have a birth date set or no year information is present.",
                isError: true
            );
        }

        var dobConverted = new DateTime(
            patientDob.Years.Value,
            patientDob.Months ?? 1,
            patientDob.Days ?? 1
        );
        var now = DateTime.UtcNow;
        var age = now.Year - dobConverted.Year;

        if (dobConverted > now.AddYears(-age))
        {
            age--;
        }

        return McpToolUtilities.CreateTextToolResponse($"The patient's age is: {age}");
    }
}
