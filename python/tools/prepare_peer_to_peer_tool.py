import os
import json
import httpx
from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def prepare_peer_to_peer(
    denial_reason: Annotated[
        str,
        Field(description="The exact denial reason from the payer."),
    ],
    patient_data: Annotated[
        str,
        Field(description="JSON string of patient data including diagnosis, labs, treatment history."),
    ],
    procedure: Annotated[
        str,
        Field(description="The procedure or medication being requested."),
    ],
    payer: Annotated[
        str,
        Field(description="Insurance payer name."),
    ],
    physician_name: Annotated[
        str | None,
        Field(description="Attending physician name."),
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
        raise ValueError("GROQ_API_KEY not set")

    try:
        patient = json.loads(patient_data)
    except Exception:
        patient = {"raw": patient_data}

    prompt = f"""You are a clinical peer-to-peer review specialist preparing a physician for a call with a payer medical director.

DENIAL REASON: {denial_reason}

PATIENT DATA:
{json.dumps(patient, indent=2)}

PROCEDURE REQUESTED: {procedure}
PAYER: {payer}
PHYSICIAN: {physician_name or "Attending Physician"}

Generate a structured peer-to-peer call preparation document. Return ONLY valid JSON:
{{
  "call_opening": "Exact suggested opening statement (2-3 sentences)",
  "key_clinical_arguments": [
    {{
      "argument": "Clinical argument",
      "supporting_evidence": "Specific data point from patient record or published guideline",
      "strength": "STRONG/MODERATE"
    }}
  ],
  "anticipated_payer_objections": [
    {{
      "objection": "What the payer medical director will likely say",
      "rebuttal": "Exact response with specific clinical evidence",
      "data_point": "Statistic or guideline citation to use"
    }}
  ],
  "non_negotiable_points": ["Points physician must not concede"],
  "call_closing": "Suggested closing statement requesting expedited reversal",
  "escalation_path": "What to do if peer-to-peer fails",
  "estimated_call_duration": "X minutes",
  "urgency_statement": "Clinical urgency argument if treatment delay poses patient risk"
}}"""

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
                "max_tokens": 1500,
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

    try:
        clean = content.replace("```json", "").replace("```", "").strip()
        prep_doc = json.loads(clean)
    except Exception:
        prep_doc = {"raw": content, "parse_error": True}

    result = {
        "patient_id": patientId,
        "procedure": procedure,
        "payer": payer,
        "denial_reason": denial_reason,
        "peer_to_peer_prep": prep_doc,
        "generated_by": "Groq (llama-3.3-70b)",
        "important_note": "Physician must verify all clinical claims before the call. This is a preparation guide, not a script.",
    }

    return create_text_response(json.dumps(result, indent=2))
