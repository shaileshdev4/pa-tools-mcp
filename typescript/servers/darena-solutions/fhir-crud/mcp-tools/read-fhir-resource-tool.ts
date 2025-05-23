import { McpServer } from "@modelcontextprotocol/sdk/server/mcp";
import { z } from "zod";
import { getFhirContext } from "../fhir-utilities";
import { createTextResponse } from "../mcp-utilities";
import { Request } from "express";
import axios from "axios";
import { IMcpTool } from "../IMcpTool";

class ReadFhirResourceTool implements IMcpTool {
  registerTool(server: McpServer, req: Request) {
    server.tool(
      "read_fhir_resource",
      "Reads a FHIR resource from a FHIR server given a resource type and resource " +
        "id. This can be used to obtain additional details of a resource.",
      {
        resourceType: z
          .string()
          .describe(
            "The FHIR resource type. (EG: Patient, Encounter, Observation, etc.)"
          ),
        resourceId: z
          .string()
          .describe(
            "The ID of the resource to retrieve. This should be a guid. If it is not " +
              "a guid or there is no resource id, use another tool to first find the " +
              "resource id"
          ),
      },
      async ({ resourceType, resourceId }) => {
        const fhirContext = getFhirContext(req);
        if (!fhirContext) {
          return createTextResponse(
            "A FHIR server url or token was not provided in the http context.",
            { isError: true }
          );
        }

        try {
          const url = `${fhirContext.url}/${resourceType}/${resourceId}`;
          const { data } = await axios(url, {
            headers: {
              Authorization: `Bearer ${fhirContext.token}`,
            },
          });

          if (!data) {
            return createTextResponse("The resource could not be found.", {
              isError: true,
            });
          }

          return createTextResponse(JSON.stringify(data));
        } catch (error) {
          return createTextResponse(
            "An unexpected error occurred while attempting to retrieve the resource.",
            { isError: true }
          );
        }
      }
    );
  }
}

export const ReadFhirResourceToolInstance = new ReadFhirResourceTool();
