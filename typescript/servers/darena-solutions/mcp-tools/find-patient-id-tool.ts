import { z } from "zod";
import { getFhirContext, getPatientIdIfContextExists } from "../fhir-utilities";
import { createTextResponse } from "../mcp-utilities";
import axios from "axios";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
import { Request } from "express";
import { IMcpTool } from "../IMcpTool";

class FindPatientIdTool implements IMcpTool {
  registerTool(server: McpServer, req: Request) {
    server.tool(
      "find_patient_id",
      "Finds an id of the patient. It is not required to supply both first name and " +
        "last name, only one of the parameters is sufficient. If patient context already " +
        "exists, then do not supply first name and last name unless the user explicitly " +
        "provides this information.",
      {
        firstName: z.string().optional().describe("The patient's first name"),
        lastName: z.string().optional().describe("The patient's last name"),
      },
      async ({ firstName, lastName }, extra) => {
        const fhirContext = getFhirContext(req);
        if (!fhirContext) {
          return createTextResponse(
            "A FHIR server url or token was not provided in the http context.",
            { isError: true }
          );
        }

        const patientIdContext = getPatientIdIfContextExists(req);
        if (patientIdContext) {
          return createTextResponse(patientIdContext);
        }

        if (!firstName && !lastName) {
          return createTextResponse(
            "No patient context found, thus the first name or last name is required.",
            { isError: true }
          );
        }

        const patientSearcher = async (
          searchFirstName: string | null | undefined,
          searchLastName: string | null | undefined
        ): Promise<{ id: string }[] | null> => {
          const searchParameters: string[] = [];
          if (searchFirstName) {
            searchParameters.push(`given=${searchFirstName}`);
          }

          if (searchLastName) {
            searchParameters.push(`family=${searchLastName}`);
          }

          const url = `${fhirContext.url}/Patient?${searchParameters.join(
            "&"
          )}`;
          const { data } = await axios.get(url, {
            headers: {
              Authorization: `Bearer ${fhirContext.token}`,
            },
          });

          return data?.entry.length
            ? (data.entry as { resource: { id: string } }[]).map(
                (x) => x.resource
              )
            : null;
        };

        try {
          let searchResponse = await patientSearcher(firstName, lastName);
          if (!searchResponse) {
            searchResponse = await patientSearcher(lastName, firstName);
          }

          if (!searchResponse || searchResponse.length === 0) {
            return createTextResponse("The patient could not be found.", {
              isError: true,
            });
          }

          if (searchResponse.length > 1) {
            return createTextResponse(
              "More than one patient found. Need more details",
              { isError: true }
            );
          }

          return createTextResponse(searchResponse[0].id);
        } catch (error) {
          return createTextResponse(
            "An unexpected error occurred while attempting to retrieve the patient's id.",
            { isError: true }
          );
        }
      }
    );
  }
}

export const FindPatientIdToolInstance = new FindPatientIdTool();
