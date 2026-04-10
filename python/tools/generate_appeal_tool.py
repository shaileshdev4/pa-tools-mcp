import os
import json
from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

async def generate_appeal_letter(
    denial_reason: Annotated[
        str,
        Field(description="The specific reason provided by the payer for denying the prior authorization."),
    ],
    patient_data: Annotated[
        str,
        Field(description="JSON string of patient data. Use output from GetPatientData tool."),
    ],
    procedure: Annotated[
        str,
        Field(description="The procedure or medication that was denied."),
    ],
    physician_name: Annotated[
        str | None,
        Field(description="Attending physician full name."),
    ] = None,
    institution: Annotated[
        str | None,
        Field(description="Healthcare institution name."),
    ] = None,
    physician_npi: Annotated[
        str | None,
        Field(description="Physician NPI number."),
    ] = None,
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

    if not physician_name:
        physician_name = patient.get("attending_physician") or "Attending Physician"
    if not institution:
        institution = patient.get("institution") or "Healthcare Institution"
    if not physician_npi:
        physician_npi = patient.get("physician_npi") or "On File"

    today = __import__('datetime').date.today().strftime('%B %d, %Y')

    prompt = f"""You are a clinical documentation specialist writing a formal appeal against a prior authorization denial.

PATIENT INFORMATION:
{json.dumps(patient, indent=2)}

PROCEDURE DENIED: {procedure}
DENIAL REASON PROVIDED BY PAYER: {denial_reason}
ATTENDING PHYSICIAN: {physician_name} | {institution} | NPI: {physician_npi}
DATE: {today}

Write a formal, compelling appeal letter that:
1. Opens by formally appealing the denial of {procedure}
2. Directly addresses and rebuts the specific denial reason: "{denial_reason}"
3. Provides clinical evidence from the patient data that contradicts the denial reason
4. Cites relevant clinical guidelines (NCCN, AMA, CMS-0057-F) supporting medical necessity
5. States the clinical risk to the patient if treatment continues to be delayed
6. Requests expedited review given clinical urgency
7. Closes with a clear demand for reversal

Rules:
- FROM: {physician_name}, {institution}
- Never use [brackets] or placeholder text
- Be forceful and specific — this is an appeal, not a request
- Cite specific lab values and dates from patient data
- Reference 82% appeal overturn rate as precedent if denial seems automated
- Under 600 words
- Sign with {physician_name}'s full credentials"""

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
        appeal_letter = data["choices"][0]["message"]["content"]

    result = {
        "patient_id": patientId,
        "procedure": procedure,
        "denial_reason_addressed": denial_reason,
        "appeal_letter": appeal_letter,
        "generated_by": "Groq (llama-3.3-70b)",
        "appeal_stats": "82% of PA appeals are overturned when properly documented (Medicare Advantage data)",
        "ready_for_submission": True,
    }

    return create_text_response(json.dumps(result, indent=2))