from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import json

async def get_patient_data(
    patientId: Annotated[
        str | None,
        Field(description="The id of the patient. Optional if patient context exists."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)
        if not patientId:
            raise ValueError("No patient context found")

    fhir_context = get_fhir_context(ctx)
    if not fhir_context:
        raise ValueError("FHIR context could not be retrieved")

    client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)

    patient = await client.read(f"Patient/{patientId}")
    if not patient:
        return create_text_response("Patient not found.", is_error=True)

    conditions = await client.search("Condition", {"patient": patientId, "_count": "20"})
    medications = await client.search("MedicationRequest", {"patient": patientId, "_count": "20"})
    encounters = await client.search("Encounter", {"patient": patientId, "_count": "5", "_sort": "-date"})
    documents = await client.search("DocumentReference", {"patient": patientId, "_count": "5", "_sort": "-date"})

    def extract_entries(bundle):
        if not bundle:
            return []
        return [e["resource"] for e in bundle.get("entry", [])]

    result = {
        "patient": {
            "id": patient.get("id"),
            "name": patient.get("name", [{}])[0].get("text") or (
                " ".join(
                    patient.get("name", [{}])[0].get("given", []) +
                    [patient.get("name", [{}])[0].get("family", "")]
                )
            ),
            "birthDate": patient.get("birthDate"),
            "gender": patient.get("gender"),
        },
        "conditions": [
            {
                "code": c.get("code", {}).get("coding", [{}])[0].get("code"),
                "display": c.get("code", {}).get("text") or c.get("code", {}).get("coding", [{}])[0].get("display"),
                "status": c.get("clinicalStatus", {}).get("coding", [{}])[0].get("code"),
            }
            for c in extract_entries(conditions)
        ],
        "medications": [
            {
                "medication": m.get("medicationCodeableConcept", {}).get("text") or
                              m.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display"),
                "status": m.get("status"),
            }
            for m in extract_entries(medications)
        ],
        "recent_encounters": [
            {
                "type": e.get("type", [{}])[0].get("text"),
                "date": e.get("period", {}).get("start"),
                "status": e.get("status"),
            }
            for e in extract_entries(encounters)
        ],
        "documents": [
            {
                "type": d.get("type", {}).get("text"),
                "date": d.get("date"),
                "status": d.get("status"),
            }
            for d in extract_entries(documents)
        ],
    }

    # Extract text from documents for clinical context
    doc_texts = []
    for d in extract_entries(documents):
        for content in d.get("content", []):
            attachment = content.get("attachment", {})
            if attachment.get("data"):
                import base64
                try:
                    text = base64.b64decode(attachment["data"]).decode("utf-8")
                    doc_texts.append(text[:500])
                except Exception:
                    pass

    result["clinical_notes_text"] = doc_texts

    return create_text_response(json.dumps(result, indent=2))