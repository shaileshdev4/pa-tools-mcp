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

    prompt = f"""You are a clinical documentation specialist writing a prior authorization request for an insurance payer.

PATIENT INFORMATION:
{json.dumps(patient, indent=2)}

PROCEDURE REQUESTED: {procedure}

Write a formal, medically accurate prior authorization justification letter that includes:
1. Patient clinical summary (age, relevant diagnoses, current medications)
2. Medical necessity statement — why this procedure is clinically required
3. Supporting clinical evidence from the patient's history
4. Prior treatments attempted and their outcomes (if available)
5. Expected clinical benefit and outcomes
6. Urgency level assessment

Format as a professional medical letter. Be specific, cite the patient's actual conditions and history.
Do not use placeholder text. Write as if this will be submitted to an insurance payer today.
Keep it under 500 words but make every word count."""

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