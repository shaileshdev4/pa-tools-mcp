"""FHIR R4 AuditEvent when physician approves a PA packet (workspace write)."""

import json
from datetime import datetime, timezone
from typing import Annotated

from mcp.server.fastmcp import Context
from pydantic import Field

from fhir_client import FhirClient
from fhir_utilities import get_fhir_context, get_patient_id_if_context_exists
from mcp_utilities import create_text_response


async def create_pa_audit_record(
    procedure: Annotated[str, Field(description="Procedure or service for the approved PA.")],
    approved_by: Annotated[str, Field(description="Name or identifier of who approved (e.g. physician display name).")],
    payer: Annotated[str, Field(description="Payer name.")],
    justification_summary: Annotated[
        str | None,
        Field(description="Short summary of justification or packet id for the audit trail."),
    ] = None,
    patient_id: Annotated[str | None, Field(description="FHIR Patient logical id.")] = None,
    patientId: Annotated[str | None, Field(description="Patient ID if not passed as patient_id.")] = None,
    ctx: Context = None,
) -> str:
    if not patient_id:
        patient_id = patientId or get_patient_id_if_context_exists(ctx)

    fhir_context = get_fhir_context(ctx)
    if not fhir_context or not fhir_context.token:
        return create_text_response(
            json.dumps(
                {
                    "status": "error",
                    "message": "FHIR context not available for audit record creation",
                },
                indent=2,
            ),
            is_error=True,
        )

    if not patient_id:
        return create_text_response(
            json.dumps(
                {
                    "status": "error",
                    "message": "patient_id required for AuditEvent",
                },
                indent=2,
            ),
            is_error=True,
        )

    now = datetime.now(timezone.utc).isoformat()

    audit_event = {
        "resourceType": "AuditEvent",
        "type": {
            "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
            "code": "110106",
            "display": "Export",
        },
        "subtype": [
            {
                "system": "http://hl7.org/fhir/restful-interaction",
                "code": "create",
                "display": "create",
            }
        ],
        "action": "C",
        "recorded": now,
        "outcome": "0",
        "agent": [{"who": {"display": approved_by}, "requestor": True}],
        "source": {"observer": {"display": "PA Authorization Orchestrator"}},
        "entity": [
            {
                "what": {"reference": f"Patient/{patient_id}"},
                "description": (
                    f"PA approved for {procedure} — Payer: {payer}"
                    + (f" — {justification_summary}" if justification_summary else "")
                ),
            }
        ],
    }

    client = FhirClient(base_url=fhir_context.url, token=fhir_context.token)
    status, body = await client.post("AuditEvent", audit_event)

    if status in (200, 201) and isinstance(body, dict):
        return create_text_response(
            json.dumps(
                {
                    "status": "audit_recorded",
                    "audit_event_id": body.get("id", "unknown"),
                    "recorded_at": now,
                    "approved_by": approved_by,
                    "procedure": procedure,
                    "payer": payer,
                    "message": "PA approval recorded as FHIR AuditEvent in workspace",
                },
                indent=2,
            )
        )

    return create_text_response(
        json.dumps(
            {
                "status": "error",
                "http_status": status,
                "message": body if body else "AuditEvent POST did not return 200/201",
            },
            indent=2,
        ),
        is_error=True,
    )
