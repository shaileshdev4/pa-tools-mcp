from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import httpx
import json

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"


def _is_relevant(
    study: dict, patient_age: int | None, country_pref: str | None
) -> tuple[bool, int]:
    """Returns (is_relevant, score). Higher score = more relevant."""
    proto = study.get("protocolSection", {})
    eligibility = proto.get("eligibilityModule", {})
    contacts = proto.get("contactsLocationsModule", {})
    locations = contacts.get("locations", [])
    countries = [loc.get("country", "") for loc in locations]

    score = 0

    # Country preference scoring
    if country_pref and any(country_pref in c for c in countries):
        score += 10

    # Age eligibility check
    if patient_age:
        min_age_str = eligibility.get("minimumAge", "0 Years")
        max_age_str = eligibility.get("maximumAge", "999 Years")
        try:
            min_age = int(min_age_str.split()[0]) if "Year" in min_age_str else 0
            max_age = int(max_age_str.split()[0]) if "Year" in max_age_str else 999
            if min_age <= patient_age <= max_age:
                score += 20
            else:
                return False, 0  # Exclude age-ineligible trials
        except (ValueError, IndexError):
            score += 5  # Age unclear, keep but lower score

    return True, score


async def match_clinical_trials(
    condition: Annotated[
        str,
        Field(description="The medical condition or diagnosis to search trials for."),
    ],
    patient_age: Annotated[
        int | None,
        Field(description="Patient age in years. Used to filter age-appropriate trials."),
    ] = None,
    patient_sex: Annotated[
        str | None,
        Field(description="Patient sex: 'male' or 'female'. Used to filter eligible trials."),
    ] = None,
    country_preference: Annotated[
        str | None,
        Field(description="Preferred country for trials. E.g. 'United States'. Returns US trials first."),
    ] = "United States",
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
        "pageSize": "10",  # fetch more, filter down to 5
        "format": "json",
        "fields": "NCTId,BriefTitle,OverallStatus,BriefSummary,EligibilityCriteria,LocationCountry,Phase,Condition,MinimumAge,MaximumAge,Sex",
    }

    if country_preference:
        params["query.locn"] = country_preference

    # Add sex filter if provided
    if patient_sex:
        sex_map = {"female": "FEMALE", "male": "MALE"}
        sex_filter = sex_map.get(patient_sex.lower())
        if sex_filter:
            params["filter.advanced"] = f"AREA[Sex]{sex_filter} OR AREA[Sex]ALL"

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

    # Score and filter studies
    scored = []
    for study in studies:
        relevant, score = _is_relevant(study, patient_age, country_preference)
        if relevant:
            scored.append((score, study))

    # Sort by score descending, take top 5
    scored.sort(key=lambda x: x[0], reverse=True)
    top_studies = [s for _, s in scored[:5]]

    trials = []
    for study in top_studies:
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
            "minimum_age": eligibility_module.get("minimumAge", "Not specified"),
            "maximum_age": eligibility_module.get("maximumAge", "Not specified"),
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

    if not trials and studies:
        result["message"] = (
            "Trials were returned but none passed age/eligibility relevance filtering."
        )

    return create_text_response(json.dumps(result, indent=2))
