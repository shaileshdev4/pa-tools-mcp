from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import httpx
import json

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"

async def match_clinical_trials(
    condition: Annotated[
        str,
        Field(description="The medical condition or diagnosis to search trials for. E.g. 'diabetes', 'breast cancer', 'hypertension'."),
    ],
    patientId: Annotated[
        str | None,
        Field(description="Patient ID. Optional if patient context exists."),
    ] = None,
    ctx: Context = None,
) -> str:
    if not patientId:
        patientId = get_patient_id_if_context_exists(ctx)

    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "pageSize": "5",
        "format": "json",
        "fields": "NCTId,BriefTitle,OverallStatus,BriefSummary,EligibilityCriteria,LocationCountry,Phase,Condition",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PA-Agent/1.0; +https://promptopinion.ai)"
    }
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        try:
            
            response = await client.get(CLINICAL_TRIALS_API, params=params)
            if response.status_code == 403:
                return create_text_response(json.dumps({
                    "condition_searched": condition,
                    "trials_found": 0,
                    "message": "ClinicalTrials.gov access restricted from this server. For production deployment, use a cloud server with unrestricted outbound access.",
                    "trials": [],
                    "note": "In production, this tool returns live recruiting trials from clinicaltrials.gov"
                }, indent=2))
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            return create_text_response(f"Failed to fetch clinical trials: {str(e)}", is_error=True)

    studies = data.get("studies", [])

    if not studies:
        return create_text_response(json.dumps({
            "condition": condition,
            "trials_found": 0,
            "message": "No active recruiting trials found for this condition.",
            "trials": [],
        }, indent=2))

    trials = []
    for study in studies:
        proto = study.get("protocolSection", {})
        id_module = proto.get("identificationModule", {})
        status_module = proto.get("statusModule", {})
        desc_module = proto.get("descriptionModule", {})
        eligibility_module = proto.get("eligibilityModule", {})
        design_module = proto.get("designModule", {})
        conditions_module = proto.get("conditionsModule", {})
        contacts_module = proto.get("contactsLocationsModule", {})

        locations = contacts_module.get("locations", [])
        countries = list(set(loc.get("country", "") for loc in locations if loc.get("country")))

        trials.append({
            "nct_id": id_module.get("nctId"),
            "title": id_module.get("briefTitle"),
            "status": status_module.get("overallStatus"),
            "phase": design_module.get("phaseList", {}).get("phase", ["N/A"])[0] if design_module.get("phaseList") else "N/A",
            "conditions": conditions_module.get("conditionList", {}).get("condition", []),
            "summary": desc_module.get("briefSummary", "")[:300] + "..." if desc_module.get("briefSummary") else "",
            "eligibility_criteria_snippet": eligibility_module.get("eligibilityCriteria", "")[:400] + "..." if eligibility_module.get("eligibilityCriteria") else "",
            "countries": countries[:5],
            "clinicaltrials_url": f"https://clinicaltrials.gov/study/{id_module.get('nctId')}",
        })

    result = {
        "condition_searched": condition,
        "patient_id": patientId,
        "trials_found": len(trials),
        "source": "clinicaltrials.gov (live data)",
        "trials": trials,
    }

    return create_text_response(json.dumps(result, indent=2))