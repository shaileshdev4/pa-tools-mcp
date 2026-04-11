import os
import json
from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

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

Write a formal prior authorization justification letter. Rules:
- Address to: Prior Authorization Department
- FROM: {from_line}
- Include: patient summary, medical necessity, clinical evidence, prior treatments, expected benefit, urgency
- Cite specific lab values, dates, and protocol names from the patient data above
- NEVER use [brackets] or placeholder text — use only real data provided
- If any field is unknown, use generic professional language — never use brackets or remove text
- If data is missing, describe it clinically rather than using placeholders
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
    }

    return create_text_response(json.dumps(result, indent=2))