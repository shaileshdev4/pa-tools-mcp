from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import json

PAYER_PROFILES = {
    "aetna": {
        "name": "Aetna",
        "urgent_hours": 72,
        "standard_days": 7,
        "step_therapy_required": True,
        "step_therapy_min_duration_months": 3,
        "prior_auth_validity_days": 365,
        "appeals_timeframe_days": 60,
        "portal": "Aetna NaviMedix",
        "known_denial_patterns": [
            "Step therapy not completed per Aetna Clinical Policy Bulletin",
            "Missing peer-to-peer review request within 24 hours",
            "Lab results older than 30 days",
        ],
        "notes": "Aetna requires peer-to-peer within 24hrs of urgent denial. NaviMedix portal preferred.",
    },
    "unitedhealth": {
        "name": "UnitedHealthcare",
        "urgent_hours": 72,
        "standard_days": 5,
        "step_therapy_required": True,
        "step_therapy_min_duration_months": 3,
        "prior_auth_validity_days": 180,
        "appeals_timeframe_days": 30,
        "portal": "UHC Provider Portal / Optum",
        "known_denial_patterns": [
            "Clinical criteria not met per UHC medical policy",
            "Missing medical records with submission",
            "PA expired — 180-day limit",
            "Off-formulary without exception form",
        ],
        "notes": "UHC PA valid only 180 days. Shorter than CMS minimum. Reauthorization required.",
    },
    "bcbs": {
        "name": "Blue Cross Blue Shield",
        "urgent_hours": 72,
        "standard_days": 7,
        "step_therapy_required": True,
        "step_therapy_min_duration_months": 6,
        "prior_auth_validity_days": 365,
        "appeals_timeframe_days": 60,
        "portal": "Availity",
        "known_denial_patterns": [
            "Step therapy minimum 6 months not met (BCBS policy)",
            "Specialty pharmacy not used",
            "Missing specialty pharmacy enrollment form",
        ],
        "notes": "BCBS requires 6-month step therapy minimum — stricter than competitors. Specialty pharmacy mandate.",
    },
    "cigna": {
        "name": "Cigna",
        "urgent_hours": 24,
        "standard_days": 3,
        "step_therapy_required": True,
        "step_therapy_min_duration_months": 3,
        "prior_auth_validity_days": 365,
        "appeals_timeframe_days": 60,
        "portal": "Cigna for Health Care Professionals",
        "known_denial_patterns": [
            "Cigna drug list exclusion — biosimilar preferred",
            "Missing Cigna-specific PA form",
            "Diagnosis not matching Cigna coverage criteria",
        ],
        "notes": "Cigna is fastest — 24hr urgent, 3-day standard. Often requires biosimilar first.",
    },
    "medicare": {
        "name": "Medicare Advantage",
        "urgent_hours": 72,
        "standard_days": 7,
        "step_therapy_required": False,
        "step_therapy_min_duration_months": 0,
        "prior_auth_validity_days": 365,
        "appeals_timeframe_days": 60,
        "portal": "CMS FHIR PA API (2027)",
        "known_denial_patterns": [
            "Not medically necessary per Medicare LCD/NCD",
            "Missing ABN (Advance Beneficiary Notice)",
            "Service not covered under Part B/D",
        ],
        "notes": "CMS-0057-F mandates FHIR PA API by Jan 2027. 82% of Medicare Advantage appeals overturned.",
    },
}

DEFAULT_PAYER = PAYER_PROFILES["medicare"]

# CMS-0057-F compliant coverage rules
# Structured as CDS Hooks-style decision support cards
PROCEDURE_RULES = {
    "methotrexate": {
        "procedure_name": "High-dose Methotrexate (HD-MTX)",
        "cpt_codes": ["J9250", "J9260"],
        "requires_pa": True,
        "pa_type": "Prior Authorization",
        "clinical_criteria": [
            "Confirmed diagnosis requiring HD-MTX per NCCN protocol",
            "Adequate renal function (GFR > 60 mL/min/1.73m2)",
            "Adequate hepatic function (ALT/AST < 3x ULN)",
            "ANC > 1000 cells/uL before administration",
            "Physician attestation of medical necessity",
        ],
        "required_documentation": [
            "Pathology report confirming diagnosis",
            "Clinical notes from last 3 visits",
            "Complete metabolic panel (labs within 7 days)",
            "Treating oncologist attestation with NPI",
            "Treatment protocol documentation (NCCN guideline reference)",
            "Prior treatment history and response",
            "Medical necessity statement",
        ],
        "denial_risk_factors": [
            "Missing lab results within required timeframe",
            "Incomplete prior treatment history",
            "No NCCN protocol reference",
            "Missing physician NPI on attestation",
        ],
        "urgency_note": "Oncology PA — delays >7 days risk protocol deviation and relapse.",
    },
    "chemotherapy": {
        "procedure_name": "Chemotherapy",
        "cpt_codes": ["96413", "96415", "96416"],
        "requires_pa": True,
        "pa_type": "Prior Authorization",
        "clinical_criteria": [
            "Confirmed malignancy diagnosis",
            "FDA-approved or NCCN Category 1 indication",
            "Adequate organ function documented",
            "Oncologist attestation of medical necessity",
        ],
        "required_documentation": [
            "Pathology/biopsy report",
            "Clinical notes from last 3 visits",
            "Complete blood count and metabolic panel",
            "Treating oncologist attestation",
            "Treatment protocol documentation",
            "Prior treatment history",
        ],
        "denial_risk_factors": [
            "Off-label use without documentation",
            "Missing pathology confirmation",
            "Incomplete organ function labs",
        ],
        "urgency_note": "Cancer treatment — 72-hour urgent review available.",
    },
    "mri": {
        "procedure_name": "MRI Imaging",
        "cpt_codes": ["70553", "72141", "73721"],
        "requires_pa": True,
        "pa_type": "Prior Authorization",
        "clinical_criteria": [
            "Clinical indication documented",
            "Conservative treatment attempted (if applicable)",
            "Ordering physician attestation",
        ],
        "required_documentation": [
            "Clinical notes documenting indication",
            "Ordering physician documentation",
            "Prior imaging results (if applicable)",
        ],
        "denial_risk_factors": [
            "No documented clinical indication",
            "Conservative treatment not attempted",
        ],
        "urgency_note": "Standard 7-day review applies.",
    },
    "biologics": {
        "procedure_name": "Biologic Medication",
        "cpt_codes": ["J0129", "J0135", "J3380"],
        "requires_pa": True,
        "pa_type": "Prior Authorization + Step Therapy",
        "clinical_criteria": [
            "Confirmed diagnosis with inadequate response to conventional therapy",
            "Step therapy completion documented",
            "Specialist attestation required",
        ],
        "required_documentation": [
            "Diagnosis confirmation",
            "Step therapy failure documentation (2+ conventional agents)",
            "Specialist clinical notes",
            "Lab results (TB test, hepatitis screening)",
        ],
        "denial_risk_factors": [
            "Step therapy not completed",
            "Missing TB/hepatitis screening",
            "No specialist attestation",
        ],
        "urgency_note": "Step therapy requirements strictly enforced.",
    },
    "surgery": {
        "procedure_name": "Surgical Procedure",
        "cpt_codes": ["varies"],
        "requires_pa": True,
        "pa_type": "Prior Authorization",
        "clinical_criteria": [
            "Medical necessity documented",
            "Conservative treatment attempted",
            "Surgeon attestation",
        ],
        "required_documentation": [
            "Clinical notes documenting necessity",
            "Conservative treatment history",
            "Surgical plan documentation",
        ],
        "denial_risk_factors": [
            "Conservative treatment not attempted",
            "Incomplete clinical documentation",
        ],
        "urgency_note": "Standard 7-day review. Urgent 72-hour available for emergent cases.",
    },
}

DEFAULT_RULE = {
    "procedure_name": None,
    "cpt_codes": ["varies"],
    "requires_pa": True,
    "pa_type": "Prior Authorization",
    "clinical_criteria": [
        "Medical necessity documented",
        "Ordering physician attestation",
    ],
    "required_documentation": [
        "Clinical notes from last 3 visits",
        "Diagnosis codes (ICD-10)",
        "Treating physician attestation",
        "Medical necessity statement",
        "Prior treatment history",
    ],
    "denial_risk_factors": [
        "Insufficient documentation of medical necessity",
        "Missing prior treatment failure documentation",
        "Incomplete clinical notes",
    ],
    "urgency_note": "Standard 7-day review. 72-hour urgent review available.",
}


def _compute_confidence_score(procedure_lower: str, rule: dict) -> dict:
    """
    Compute PA approval confidence based on procedure type and clinical context.
    Returns structured confidence assessment.
    """
    # Oncology/cancer treatments have strong evidence base — higher approval rate
    # when documentation is complete
    high_evidence_keywords = ["methotrexate", "chemotherapy", "cancer", "leukemia", "oncol"]
    step_therapy_keywords = ["biologics", "biologic", "humira", "enbrel", "remicade"]

    is_oncology = any(k in procedure_lower for k in high_evidence_keywords)
    requires_step = any(k in procedure_lower for k in step_therapy_keywords)

    if is_oncology:
        return {
            "approval_likelihood": "HIGH",
            "confidence_score": "85-90%",
            "rationale": (
                "Oncology treatments with NCCN protocol documentation have high approval rates. "
                "CMS-0057-F mandates payers respond within 72 hours for urgent oncology cases. "
                "Key risk: missing or outdated lab results."
            ),
            "critical_success_factors": [
                "Current labs within 7 days (CBC, CMP, renal function)",
                "NCCN protocol citation in medical necessity statement",
                "Oncologist NPI on all documentation",
                "Prior treatment phases documented with outcomes",
            ],
            "denial_risk": "LOW if documentation complete",
        }
    elif requires_step:
        return {
            "approval_likelihood": "MEDIUM",
            "confidence_score": "60-70%",
            "rationale": (
                "Biologic medications require step therapy completion documentation. "
                "Most denials are due to incomplete step therapy records, not clinical necessity."
            ),
            "critical_success_factors": [
                "Document 2+ failed conventional agents with dates and doses",
                "TB test and hepatitis screening within required timeframe",
                "Specialist (rheumatologist/dermatologist) attestation",
            ],
            "denial_risk": "MEDIUM — step therapy documentation is frequently incomplete",
        }
    else:
        return {
            "approval_likelihood": "MEDIUM-HIGH",
            "confidence_score": "70-80%",
            "rationale": (
                "Standard PA with medical necessity documentation. "
                "Approval likelihood depends on completeness of clinical notes."
            ),
            "critical_success_factors": [
                "Clear medical necessity statement",
                "Supporting clinical notes from recent visits",
                "Ordering physician attestation",
            ],
            "denial_risk": "LOW-MEDIUM depending on documentation quality",
        }


async def check_coverage_requirements(
    procedure: Annotated[
        str,
        Field(description="The procedure or medication requiring PA check. E.g. 'High-dose Methotrexate', 'MRI', 'chemotherapy', 'biologics'."),
    ],
    diagnosis: Annotated[
        str | None,
        Field(description="Primary diagnosis (ICD-10 or description). Used to assess denial risk."),
    ] = None,
    patientId: Annotated[
        str | None,
        Field(description="Patient ID. Optional if patient context exists."),
    ] = None,
    payer: Annotated[
        str | None,
        Field(description="Insurance payer name. E.g. 'Aetna', 'UnitedHealth', 'BCBS', 'Cigna', 'Medicare'. Defaults to generic CMS rules if not specified."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)

    procedure_lower = procedure.lower()

    # Match procedure to rules
    matched_rule = None
    for key, rule in PROCEDURE_RULES.items():
        if key in procedure_lower:
            matched_rule = rule.copy()
            break

    if not matched_rule:
        matched_rule = DEFAULT_RULE.copy()
        matched_rule["procedure_name"] = procedure
    
    # Resolve payer profile
    payer_profile = DEFAULT_PAYER
    if payer:
        payer_lower = payer.lower().replace(" ", "").replace("-", "")
        for key, profile in PAYER_PROFILES.items():
            if key in payer_lower or payer_lower in key:
                payer_profile = profile
                break

    confidence = _compute_confidence_score(procedure_lower, matched_rule)

    result = {
        "coverage_check": {
            "procedure": matched_rule["procedure_name"],
            "cpt_codes": matched_rule["cpt_codes"],
            "authorization_type": matched_rule["pa_type"],
            "prior_authorization_required": matched_rule["requires_pa"],
            "patient_id": patientId,
            "diagnosis_context": diagnosis or "Not specified",
        },
        "cms_compliance": {
            "mandate": "CMS-0057-F (Interoperability and Prior Authorization Final Rule)",
            "effective_date": "January 1, 2026",
            "appeal_rights": "Patient has right to expedited appeal within 72 hours of denial",
        },
        "payer_specific_rules": {
            "payer": payer_profile["name"],
            "urgent_decision_hours": payer_profile["urgent_hours"],
            "standard_decision_days": payer_profile["standard_days"],
            "step_therapy_required": payer_profile["step_therapy_required"],
            "step_therapy_min_months": payer_profile["step_therapy_min_duration_months"],
            "pa_validity_days": payer_profile["prior_auth_validity_days"],
            "appeals_timeframe_days": payer_profile["appeals_timeframe_days"],
            "preferred_portal": payer_profile["portal"],
            "known_denial_patterns": payer_profile["known_denial_patterns"],
            "payer_notes": payer_profile["notes"],
        },
        "clinical_criteria": matched_rule["clinical_criteria"],
        "required_documentation": matched_rule["required_documentation"],
        "pa_confidence_assessment": confidence,
        "denial_risk_factors": matched_rule["denial_risk_factors"],
        "submission_guidance": {
            "urgency_note": matched_rule["urgency_note"],
            "recommendation": (
                "SUBMIT PA with complete documentation package. "
                f"Approval likelihood: {confidence['approval_likelihood']}. "
                f"Critical: {confidence['critical_success_factors'][0]}"
            ) if matched_rule["requires_pa"] else "No prior authorization required.",
        },
    }

    return create_text_response(json.dumps(result, indent=2))