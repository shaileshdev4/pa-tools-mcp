from mcp.server.fastmcp import FastMCP
from tools.patient_age_tool import get_patient_age
from tools.patient_allergies_tool import get_patient_allergies
from tools.get_patient_data_tool import get_patient_data
from tools.check_coverage_tool import check_coverage_requirements
from tools.match_clinical_trials_tool import match_clinical_trials
from tools.generate_justification_tool import generate_clinical_justification
from tools.generate_appeal_tool import generate_appeal_letter
from tools.check_documentation_tool import check_documentation_completeness
from tools.submit_pa_request_tool import submit_pa_request
from tools.create_pa_audit_record_tool import create_pa_audit_record

mcp = FastMCP("PA Tools MCP", stateless_http=True, host="0.0.0.0")

_original_get_capabilities = mcp._mcp_server.get_capabilities

def _patched_get_capabilities(notification_options, experimental_capabilities):
    caps = _original_get_capabilities(notification_options, experimental_capabilities)
    caps.model_extra["extensions"] = {"ai.promptopinion/fhir-context": {}}
    return caps

mcp._mcp_server.get_capabilities = _patched_get_capabilities

# Original tools
mcp.tool(name="GetPatientAge", description="Gets the age of a patient.")(get_patient_age)
mcp.tool(name="GetPatientAllergies", description="Gets the known allergies of a patient.")(get_patient_allergies)

# PA tools
mcp.tool(name="GetPatientData", description="Gets comprehensive patient data from FHIR including conditions, medications, encounters and documents.")(get_patient_data)
mcp.tool(name="CheckCoverageRequirements", description="Checks prior authorization requirements for a given procedure or service.")(check_coverage_requirements)
mcp.tool(name="MatchClinicalTrials", description="Searches ClinicalTrials.gov for active recruiting trials matching a patient's condition.")(match_clinical_trials)
mcp.tool(name="GenerateClinicalJustification", description="Generates a formal clinical justification letter for prior authorization using AI.")(generate_clinical_justification)
mcp.tool(name="GenerateAppealLetter", description="Generates a formal appeal letter for prior authorization using AI.")(generate_appeal_letter)
mcp.tool(name="CheckDocumentationCompleteness", description="Checks the completeness of the documentation for a given procedure or service.")(check_documentation_completeness)
mcp.tool(
    name="SubmitPARequest",
    description=(
        "Builds a Da Vinci PAS–style FHIR Claim bundle and POSTs to a PAS reference server "
        "($submit). Use for CMS-0057-F alignment demos; production uses payer endpoints in 2027."
    ),
)(submit_pa_request)
mcp.tool(
    name="CreatePAAuditRecord",
    description=(
        "Creates a FHIR R4 AuditEvent in the workspace when a physician approves a PA packet "
        "(requires FHIR write context)."
    ),
)(create_pa_audit_record)