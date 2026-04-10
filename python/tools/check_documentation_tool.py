import json
from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response

REQUIRED_DOCS = {
    "methotrexate": [
        {"item": "Pathology/biopsy report confirming diagnosis", "fhir_resource": "DocumentReference", "keywords": ["pathology", "biopsy", "diagnosis"]},
        {"item": "Labs within 7 days (CBC, CMP, renal function)", "fhir_resource": "Observation", "keywords": ["wbc", "creatinine", "alt", "ast", "anc", "gfr"]},
        {"item": "Treating oncologist attestation with NPI", "fhir_resource": "DocumentReference", "keywords": ["attestation", "npi", "oncologist"]},
        {"item": "NCCN protocol reference", "fhir_resource": "DocumentReference", "keywords": ["nccn", "protocol", "guideline"]},
        {"item": "Prior treatment history with outcomes", "fhir_resource": "MedicationRequest", "keywords": ["induction", "consolidation", "prior", "treatment"]},
        {"item": "Medical necessity statement", "fhir_resource": "DocumentReference", "keywords": ["necessity", "medically necessary", "required"]},
        {"item": "Clinical notes from last 3 visits", "fhir_resource": "Encounter", "keywords": ["encounter", "visit", "note"]},
    ],
    "chemotherapy": [
        {"item": "Pathology report confirming malignancy", "fhir_resource": "DocumentReference", "keywords": ["pathology", "malignancy", "cancer"]},
        {"item": "Labs within 7 days (CBC, CMP)", "fhir_resource": "Observation", "keywords": ["wbc", "creatinine", "anc"]},
        {"item": "Oncologist attestation", "fhir_resource": "DocumentReference", "keywords": ["attestation", "oncologist"]},
        {"item": "Treatment protocol documentation", "fhir_resource": "DocumentReference", "keywords": ["protocol", "nccn", "guideline"]},
        {"item": "Prior treatment history", "fhir_resource": "MedicationRequest", "keywords": ["prior", "treatment", "history"]},
        {"item": "Medical necessity statement", "fhir_resource": "DocumentReference", "keywords": ["necessity", "required"]},
    ],
    "biologics": [
        {"item": "Step therapy documentation (2+ failed agents)", "fhir_resource": "MedicationRequest", "keywords": ["methotrexate", "sulfasalazine", "hydroxychloroquine", "failed", "inadequate"]},
        {"item": "TB test within 6 months", "fhir_resource": "Observation", "keywords": ["tuberculosis", "tb", "quantiferon", "ppd"]},
        {"item": "Hepatitis B/C screening", "fhir_resource": "Observation", "keywords": ["hepatitis", "hbsag", "hcv"]},
        {"item": "Specialist attestation (rheumatologist/dermatologist)", "fhir_resource": "DocumentReference", "keywords": ["rheumatologist", "dermatologist", "specialist"]},
        {"item": "Diagnosis confirmation with severity", "fhir_resource": "Condition", "keywords": ["rheumatoid", "psoriasis", "crohn", "moderate", "severe"]},
    ],
    "default": [
        {"item": "Clinical notes from last 3 visits", "fhir_resource": "Encounter", "keywords": ["encounter", "visit"]},
        {"item": "Diagnosis codes (ICD-10)", "fhir_resource": "Condition", "keywords": ["condition", "diagnosis"]},
        {"item": "Treating physician attestation", "fhir_resource": "DocumentReference", "keywords": ["attestation", "physician"]},
        {"item": "Medical necessity statement", "fhir_resource": "DocumentReference", "keywords": ["necessity", "required"]},
        {"item": "Prior treatment history", "fhir_resource": "MedicationRequest", "keywords": ["prior", "treatment"]},
    ],
}


def _check_item_present(item_keywords: list, patient_data: dict) -> bool:
    patient_str = json.dumps(patient_data).lower()
    return any(kw.lower() in patient_str for kw in item_keywords)


async def check_documentation_completeness(
    patient_data: Annotated[
        str,
        Field(description="JSON string of patient data from GetPatientData tool."),
    ],
    procedure: Annotated[
        str,
        Field(description="The procedure requiring prior authorization."),
    ],
    patientId: Annotated[
        str | None,
        Field(description="Patient ID. Optional if patient context exists."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)

    try:
        patient = json.loads(patient_data)
    except json.JSONDecodeError:
        patient = {"raw": patient_data}

    procedure_lower = procedure.lower()
    required = None
    for key in REQUIRED_DOCS:
        if key != "default" and key in procedure_lower:
            required = REQUIRED_DOCS[key]
            break
    if not required:
        required = REQUIRED_DOCS["default"]

    checklist = []
    missing = []
    present = []

    for doc in required:
        found = _check_item_present(doc["keywords"], patient)
        status = "✓ PRESENT" if found else "✗ MISSING"
        checklist.append({
            "item": doc["item"],
            "fhir_resource": doc["fhir_resource"],
            "status": status,
        })
        if found:
            present.append(doc["item"])
        else:
            missing.append(doc["item"])

    total = len(checklist)
    present_count = len(present)
    completeness_pct = round((present_count / total) * 100)

    if completeness_pct == 100:
        risk = "LOW — Documentation appears complete. Ready for submission."
        recommendation = "Proceed with PA submission."
    elif completeness_pct >= 70:
        risk = "MEDIUM — Missing some documentation. Denial risk elevated."
        recommendation = f"Obtain missing items before submission: {', '.join(missing)}"
    else:
        risk = "HIGH — Significant documentation gaps. Likely denial."
        recommendation = f"Do not submit until these are obtained: {', '.join(missing)}"

    result = {
        "patient_id": patientId,
        "procedure": procedure,
        "documentation_completeness": f"{completeness_pct}%",
        "items_present": present_count,
        "items_total": total,
        "checklist": checklist,
        "missing_items": missing,
        "denial_risk": risk,
        "recommendation": recommendation,
        "submission_ready": completeness_pct == 100,
    }

    return create_text_response(json.dumps(result, indent=2))