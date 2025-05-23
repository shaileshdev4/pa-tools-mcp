import { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
import { Request } from "express";
import { IMcpTool } from "../../IMcpTool";
import { z } from "zod";
import {
  getFhirContext,
  getPatientIdIfContextExists,
} from "../../fhir-utilities";
import { createTextResponse } from "../../mcp-utilities";
import axios from "axios";
import { FhirContext } from "../../fhir-context";
import { differenceInYears, parseISO } from "date-fns";

type Patient = {
  id: string;
  birthDate?: string;
};

class PatientAgeTool implements IMcpTool {
  registerTool(server: McpServer, req: Request) {
    server.tool(
      "GetPatientAge",
      "Gets the age of a patient. If patient context already exists, then the first name and last name is not required.",
      {
        firstName: z.string().optional().describe("The patient's first name"),
        lastName: z.string().optional().describe("The patient's last name"),
      },
      async ({ firstName, lastName }) => {
        const fhirContext = getFhirContext(req);
        if (!fhirContext) {
          return createTextResponse(
            "A FHIR server url or token was not provided in the http context.",
            { isError: true },
          );
        }

        const patientIdContext = getPatientIdIfContextExists(req);
        let patient: Patient | null = null;
        if (patientIdContext) {
          try {
            const response = await axios.get(
              `${fhirContext.url}/Patient/${patientIdContext}`,
              { headers: { Authorization: `Bearer ${fhirContext.token}` } },
            );

            patient = response.data;
          } catch {
            return createTextResponse(
              "Could not retrieve the patient from the context.",
            );
          }
        } else {
          if (!firstName && !lastName) {
            return createTextResponse(
              "Patient context was not found, thus the first name, last name, or both is required.",
              { isError: true },
            );
          }

          let patients = await this._patientSearcher(
            fhirContext,
            firstName,
            lastName,
          );

          if (!patients?.length) {
            patients = await this._patientSearcher(
              fhirContext,
              lastName,
              firstName,
            );
          }

          if (patients && patients.length > 1) {
            return createTextResponse(
              "More than one patient was found. Provide more details.",
              { isError: true },
            );
          }

          patient = patients?.length ? patients[0] : null;
        }

        if (!patient) {
          return createTextResponse("The patient could not be found.", {
            isError: true,
          });
        }

        if (!patient.birthDate) {
          return createTextResponse(
            "A birth date could not be found for the patient.",
            { isError: true },
          );
        }

        try {
          const date = parseISO(patient.birthDate);
          const age = differenceInYears(new Date(), date);

          return createTextResponse(`The patient's age is: ${age}`);
        } catch {
          return createTextResponse(
            "Could not parse the patient's birth date.",
            { isError: true },
          );
        }
      },
    );
  }

  private async _patientSearcher(
    fhirContext: FhirContext,
    searchFirstName: string | null | undefined,
    searchLastName: string | null | undefined,
  ): Promise<Patient[] | null> {
    const searchParameters: string[] = [];
    if (searchFirstName) {
      searchParameters.push(`given=${searchFirstName}`);
    }

    if (searchLastName) {
      searchParameters.push(`family=${searchLastName}`);
    }

    const url = `${fhirContext.url}/Patient?${searchParameters.join("&")}`;
    const { data } = await axios.get(url, {
      headers: {
        Authorization: `Bearer ${fhirContext.token}`,
      },
    });

    return data?.entry.length
      ? (data.entry as { resource: Patient }[]).map((x) => x.resource)
      : null;
  }
}

export const PatientAgeToolInstance = new PatientAgeTool();
