using Hl7.Fhir.Model;
using MeldRx.Community.Mcp.Core.Models;

namespace MeldRx.Community.McpTools.DarenaSolutions;

public interface IPatientSearchService
{
    Task<Patient?> FindByIdAsync(FhirContext context, string id);

    Task<List<Patient>> SearchByNameAsync(
        FhirContext context,
        string? firstName,
        string? lastName = null
    );
}
