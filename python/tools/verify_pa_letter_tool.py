import os
import json
from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from mcp_utilities import create_text_response
import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def verify_pa_letter(
    justification_letter: Annotated[
        str,
        Field(description="The generated PA justification letter text to verify."),
    ],
    patient_data: Annotated[
        str,
        Field(description="JSON string of patient data used to generate the letter."),
    ],
    ctx: Context = None,
) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")

    try:
        patient = json.loads(patient_data)
    except Exception:
        patient = {"raw": patient_data}

    prompt = f"""You are a clinical safety reviewer.

PATIENT SOURCE DATA:
{json.dumps(patient, indent=2)}

GENERATED LETTER TO VERIFY:
{justification_letter}

For each factual clinical claim in the letter (diagnoses, medications, lab values, dates, dosages, treatment history, guideline references), classify it as:
- VERIFIED: directly present in patient source data — include the exact field name
- INFERRED: logical inference from data but not explicitly stated
- UNSUPPORTED: not present in patient data at all

Return ONLY valid JSON:
{{
  "verified_claims": [{{"claim": "...", "source_field": "..."}}],
  "inferred_claims": [{{"claim": "...", "reasoning": "..."}}],
  "unsupported_claims": [{{"claim": "...", "risk": "HIGH/MEDIUM"}}],
  "safety_score": 0.0-1.0,
  "verdict": "SAFE_TO_REVIEW / REQUIRES_ATTENTION / DO_NOT_SUBMIT",
  "summary": "one sentence"
}}"""

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

    try:
        clean = content.replace("```json", "").replace("```", "").strip()
        verification = json.loads(clean)
    except Exception:
        verification = {"raw": content, "safety_score": 0.5, "verdict": "REQUIRES_ATTENTION"}

    result = {
        "verification": verification,
        "unsupported_count": len(verification.get("unsupported_claims", [])),
        "safety_score": verification.get("safety_score", 0),
        "verdict": verification.get("verdict", "REQUIRES_ATTENTION"),
        "physician_action": (
            "Review unsupported claims before signing"
            if verification.get("unsupported_claims")
            else "Letter verified against source data"
        ),
    }

    return create_text_response(json.dumps(result, indent=2))
