"""
HL7 Da Vinci PAS–style Claim bundle construction and optional $submit to a reference server.
Does not guarantee the public reference endpoint accepts STU2; demonstrates the protocol shape.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

import httpx
from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response

PAS_SERVER_DEFAULT = "https://prior-auth.davinci.hl7.org/fhir"


async def submit_pa_request(
    procedure: Annotated[str, Field(description="Procedure or service description for the PA request.")],
    diagnosis_code: Annotated[str, Field(description="Primary ICD-10-CM diagnosis code (no period).")],
    physician_npi: Annotated[str, Field(description="Attending physician NPI (10 digits).")],
    payer: Annotated[str, Field(description="Payer or insurer name.")],
    patient_id: Annotated[str | None, Field(description="FHIR Patient logical id.")] = None,
    cpt_or_hcpcs_code: Annotated[
        str | None,
        Field(description="CPT or HCPCS code for the requested service (e.g. J9250 for HD-MTX)."),
    ] = None,
    patientId: Annotated[str | None, Field(description="Patient ID if not passed as patient_id.")] = None,
    ctx: Context = None,
) -> str:
    if not patient_id:
        patient_id = patientId or get_patient_id_if_context_exists(ctx)
    if not patient_id:
        return create_text_response(
            json.dumps(
                {
                    "status": "error",
                    "message": "patient_id or patient context required for SubmitPARequest",
                },
                indent=2,
            ),
            is_error=True,
        )

    code = (cpt_or_hcpcs_code or "J9250").strip()
    bundle_id = str(uuid.uuid4())
    claim_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "collection",
        "entry": [
            {
                "resource": {
                    "resourceType": "Claim",
                    "id": claim_id,
                    "status": "active",
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/claim-type",
                                "code": "professional",
                            }
                        ]
                    },
                    "use": "preauthorization",
                    "patient": {"reference": f"Patient/{patient_id}"},
                    "created": now,
                    "insurer": {"display": payer},
                    "provider": {
                        "identifier": {
                            "system": "http://hl7.org/fhir/sid/us-npi",
                            "value": physician_npi,
                        }
                    },
                    "priority": {"coding": [{"code": "normal"}]},
                    "diagnosis": [
                        {
                            "sequence": 1,
                            "diagnosisCodeableConcept": {
                                "coding": [
                                    {
                                        "system": "http://hl7.org/fhir/sid/icd-10-cm",
                                        "code": diagnosis_code,
                                    }
                                ]
                            },
                        }
                    ],
                    "procedure": [
                        {
                            "sequence": 1,
                            "procedureCodeableConcept": {
                                "coding": [
                                    {
                                        "system": "http://www.ama-assn.org/go/cpt",
                                        "code": code,
                                        "display": procedure,
                                    }
                                ]
                            },
                        }
                    ],
                    "item": [
                        {
                            "sequence": 1,
                            "diagnosisSequence": [1],
                            "productOrService": {
                                "coding": [
                                    {
                                        "system": "http://www.ama-assn.org/go/cpt",
                                        "code": code,
                                        "display": procedure,
                                    }
                                ]
                            },
                        }
                    ],
                }
            }
        ],
    }

    pas_server = PAS_SERVER_DEFAULT.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{pas_server}/Claim/$submit",
                json=bundle,
                headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
            )
            if response.status_code in (200, 201):
                try:
                    result = response.json()
                except Exception:
                    result = {"raw": response.text[:500]}
                return create_text_response(
                    json.dumps(
                        {
                            "status": "submitted",
                            "standard": "HL7 Da Vinci PAS IG (bundle-shaped Claim for demo)",
                            "cms_mandate": "CMS-0057-F Prior Authorization API",
                            "bundle_id": bundle_id,
                            "claim_id": claim_id,
                            "server_response": result.get("resourceType")
                            if isinstance(result, dict)
                            else None,
                            "message": "PA request POSTed to Da Vinci PAS reference server (verify server STU/version).",
                        },
                        indent=2,
                    )
                )
            return create_text_response(
                json.dumps(
                    {
                        "status": "pending_review",
                        "standard": "HL7 Da Vinci PAS IG (bundle-shaped Claim for demo)",
                        "bundle_id": bundle_id,
                        "claim_id": claim_id,
                        "server_status": response.status_code,
                        "response_body": response.text[:800],
                        "note": (
                            "Da Vinci PAS Bundle constructed for CMS-0057-F alignment. "
                            "Reference server returned non-success; many public servers lag STU2. "
                            "In production, submit to payer FHIR endpoint when mandated APIs go live January 2027."
                        ),
                    },
                    indent=2,
                )
            )
    except Exception as e:
        return create_text_response(
            json.dumps(
                {
                    "status": "bundle_constructed",
                    "standard": "HL7 Da Vinci PAS IG (bundle-shaped Claim for demo)",
                    "bundle_id": bundle_id,
                    "claim_id": claim_id,
                    "note": (
                        "Da Vinci PAS Bundle constructed per CMS-0057-F direction. "
                        f"Reference server unreachable or error: {str(e)[:200]}. "
                        "Bundle JSON is valid for review and future payer submission."
                    ),
                    "bundle_preview": bundle,
                },
                indent=2,
            )
        )
