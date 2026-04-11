import os
import json
from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

SAFETY_INSTRUCTION = """
CRITICAL SAFETY INSTRUCTION — READ BEFORE GENERATING:
1. Only include clinical facts EXPLICITLY present in the PATIENT INFORMATION JSON above.
2. Do not infer, extrapolate, or assume any clinical history not directly stated.
3. If a required field is missing or unclear, write exactly: [REQUIRES PHYSICIAN VERIFICATION]
4. Every medication, date, dosage, lab value, and guideline reference must be traceable to the patient data.
5. Do not cite specific NCCN guideline version numbers — cite "current NCCN guidelines" only.
6. This is a DRAFT for physician review — accuracy is the physician's final responsibility.
"""


async def generate_clinical_justification(
    patient_data: Annotated[
        str,
        Field(description="JSON string of patient data including conditions, medications, encounters. Use output from GetPatientData tool."),
    ],
    procedure: Annotated[
        str,
        Field(description="The procedure or service requiring prior authorization."),
    ],
    physician_name: Annotated[str | None, Field(description="Attending physician full name. Extract from patient records.")] = None,
    institution: Annotated[str | None, Field(description="Healthcare institution or hospital name.")] = None,
    physician_npi: Annotated[str | None, Field(description="Physician NPI number if available.")] = None,
    patientId: Annotated[
        str | None,
        Field(description="Patient ID. Optional if patient context exists."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    try:
        patient = json.loads(patient_data)
    except json.JSONDecodeError:
        patient = {"raw": patient_data}

    # Try to extract from patient_data if not passed explicitly
    if not physician_name:
        physician_name = (
            patient.get("attending_physician")
            or patient.get("physician")
            or patient.get("provider")
            or "Attending Physician"
        )
    if not institution:
        institution = (
            patient.get("institution")
            or patient.get("facility")
            or patient.get("hospital")
            or patient.get("organization")
            or None
        )
    if not physician_npi:
        physician_npi = patient.get("physician_npi") or patient.get("npi") or None

    physician_line = physician_name
    if institution:
        physician_line += f"\n{institution}"
    if physician_npi:
        physician_line += f"\nNPI: {physician_npi}"

    from_line = physician_name
    if institution:
        from_line += f", {institution}"

    today = __import__('datetime').date.today().strftime('%B %d, %Y')

    prompt = f"""You are a clinical documentation specialist writing a prior authorization request for an insurance payer.

PATIENT INFORMATION:
{json.dumps(patient, indent=2)}

PROCEDURE REQUESTED: {procedure}

ATTENDING PHYSICIAN: {physician_line}
DATE: {today}
- Address to: Prior Authorization Department, [Payer Name] - if payer name unknown, write "Prior Authorization Department"

{SAFETY_INSTRUCTION}

Write a formal prior authorization justification letter. Rules:
- Address to: Prior Authorization Department
- FROM: {from_line}
- Include: patient summary, medical necessity, clinical evidence, prior treatments, expected benefit, urgency
- Cite specific lab values, dates, and protocol names only when they appear in the patient data above
- Do not invent facts; use [REQUIRES PHYSICIAN VERIFICATION] only when a required fact is missing from the JSON
- If institution is not provided, sign with physician name only — never write 'Healthcare Institution'
- If NPI is not provided, omit it — never write 'On File' or 'NPI: None'
- Sign with {physician_name}'s name and credentials
- Under 500 words"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.3,
            },
        )
        response.raise_for_status()
        data = response.json()
        justification = data["choices"][0]["message"]["content"]

    result = {
        "patient_id": patientId,
        "procedure": procedure,
        "justification_letter": justification,
        "generated_by": "Groq (llama-3.3-70b)",
        "ready_for_submission": True,
        "safety_flags": {
            "requires_physician_review": True,
            "generated_from": "structured patient data — not clinical judgment",
            "hallucination_risk": "LOW — letter must contain only fields present in patient JSON",
            "verify_before_submission": "Physician must verify all clinical claims independently",
        },
    }

    return create_text_response(json.dumps(result, indent=2))