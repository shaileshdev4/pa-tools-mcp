from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists, get_fhir_context
from mcp_utilities import create_text_response
import json

# Realistic mock payer rules — real CRD APIs don't exist publicly until 2027
PAYER_RULES = {
    "default": {
        "requires_pa": True,
        "decision_timeframe_urgent_hours": 72,
        "decision_timeframe_standard_days": 7,
        "documentation_required": [
            "Clinical notes from last 3 visits",
            "Diagnosis codes (ICD-10)",
            "Treating physician attestation",
            "Medical necessity statement",
            "Prior treatment history and failures",
        ],
        "common_denial_reasons": [
            "Insufficient documentation of medical necessity",
            "Missing prior treatment failure documentation",
            "Incomplete clinical notes",
        ],
    }
}

PROCEDURE_PA_MAP = {
    "MRI": {"requires_pa": True, "procedure_name": "MRI Imaging"},
    "CT": {"requires_pa": True, "procedure_name": "CT Scan"},
    "surgery": {"requires_pa": True, "procedure_name": "Surgical Procedure"},
    "physical therapy": {"requires_pa": True, "procedure_name": "Physical Therapy"},
    "chemotherapy": {"requires_pa": True, "procedure_name": "Chemotherapy"},
    "biologics": {"requires_pa": True, "procedure_name": "Biologic Medication"},
    "specialist": {"requires_pa": True, "procedure_name": "Specialist Referral"},
    "home health": {"requires_pa": True, "procedure_name": "Home Health Services"},
    "durable medical equipment": {"requires_pa": True, "procedure_name": "DME"},
    "lab": {"requires_pa": False, "procedure_name": "Laboratory Tests"},
    "office visit": {"requires_pa": False, "procedure_name": "Office Visit"},
}

async def check_coverage_requirements(
    procedure: Annotated[
        str,
        Field(description="The procedure or service to check PA requirements for. E.g. 'MRI', 'surgery', 'chemotherapy', 'biologics', 'specialist'."),
    ],
    patientId: Annotated[
        str | None,
        Field(description="Patient ID. Optional if patient context exists."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)

    procedure_lower = procedure.lower()
    matched = None
    for key in PROCEDURE_PA_MAP:
        if key in procedure_lower:
            matched = PROCEDURE_PA_MAP[key]
            break

    if not matched:
        matched = {"requires_pa": True, "procedure_name": procedure}

    rules = PAYER_RULES["default"]

    result = {
        "procedure": matched["procedure_name"],
        "requires_prior_authorization": matched["requires_pa"],
        "patient_id": patientId,
        "payer_rules": {
            "urgent_decision_hours": rules["decision_timeframe_urgent_hours"],
            "standard_decision_days": rules["decision_timeframe_standard_days"],
            "cms_mandate": "CMS-0057-F effective 2026",
            "documentation_required": rules["documentation_required"],
            "common_denial_reasons": rules["common_denial_reasons"],
        },
        "recommendation": (
            "Prior authorization required. Prepare complete documentation package to avoid denial."
            if matched["requires_pa"]
            else "No prior authorization required for this service."
        ),
    }

    return create_text_response(json.dumps(result, indent=2))