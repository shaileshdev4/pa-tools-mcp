using DarenaHealth.Community.Mcp.Core.Models;
using Hl7.Fhir.Model;

namespace DarenaHealth.Community.McpTools.DarenaSolutions;

public interface IPatientSearchService
{
    Task<Patient?> FindByIdAsync(FhirContext context, string id);

    Task<List<Patient>> SearchByNameAsync(
        FhirContext context,
        string? firstName,
        string? lastName = null
    );
}
