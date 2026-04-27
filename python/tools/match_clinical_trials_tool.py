from typing import Annotated
from mcp.server.fastmcp import Context
from pydantic import Field
from fhir_utilities import get_patient_id_if_context_exists
from mcp_utilities import create_text_response
import httpx
import json

CLINICAL_TRIALS_API = "https://clinicaltrials.gov/api/v2/studies"


def _is_relevant(
    study: dict, patient_age: int | None, country_pref: str | None, patient_sex: str | None, condition: str
) -> tuple[bool, int]:
    """Returns (is_relevant, score). Higher score = more relevant."""
    proto = study.get("protocolSection", {})
    eligibility = proto.get("eligibilityModule", {})
    conditions_module = proto.get("conditionsModule", {})
    design_module = proto.get("designModule", {})
    contacts = proto.get("contactsLocationsModule", {})
    locations = contacts.get("locations", [])
    countries = [loc.get("country", "") for loc in locations]
    conditions_raw = []
    if isinstance(conditions_module.get("conditions"), list):
        conditions_raw.extend(conditions_module.get("conditions", []))
    condition_list = conditions_module.get("conditionList", {})
    if isinstance(condition_list, dict) and isinstance(condition_list.get("condition"), list):
        conditions_raw.extend(condition_list.get("condition", []))
    study_conditions = [c.lower() for c in conditions_raw if isinstance(c, str)]
    summary_blob = " ".join(study_conditions)
    query_condition = (condition or "").lower()

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

    # Sex compatibility check
    if patient_sex:
        sex_value = (eligibility.get("sex") or "").lower()
        patient_sex_lower = patient_sex.lower()
        if sex_value and sex_value not in {"all", patient_sex_lower}:
            return False, 0
        if sex_value in {"all", patient_sex_lower}:
            score += 8

    # Prefer studies matching ALL/B-cell context, de-rank unrelated populations.
    if "acute lymphoblastic leukemia" in query_condition:
        if "acute lymphoblastic leukemia" in summary_blob or "all" in summary_blob:
            score += 25
        else:
            score -= 15
        if "b-cell" in summary_blob or "b cell" in summary_blob:
            score += 10
        if "t cell" in summary_blob or "t-cell" in summary_blob:
            score -= 12

    # Prefer phase 2/3 for actionable adult treatment options.
    phases_raw = []
    if isinstance(design_module.get("phases"), list):
        phases_raw.extend(design_module.get("phases", []))
    phase_list = design_module.get("phaseList", {})
    if isinstance(phase_list, dict) and isinstance(phase_list.get("phase"), list):
        phases_raw.extend(phase_list.get("phase", []))
    phases = [p.lower() for p in phases_raw if isinstance(p, str)]
    if any("phase 3" in p for p in phases):
        score += 10
    elif any("phase 2" in p for p in phases):
        score += 7
    elif any("phase 1" in p for p in phases):
        score -= 4

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
        relevant, score = _is_relevant(study, patient_age, country_preference, patient_sex, condition)
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
