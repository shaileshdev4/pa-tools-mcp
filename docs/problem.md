# The Problem We're Solving

While the MCP standard has emerged as a powerful tool for connecting LLMs to tools,
APIs, and data, no defined standard exists for building reusable and pluggable MCP
servers, especially in healthcare.

Current Observations:

- **FHIR is a dominant data source:** Most MCP servers are currently designed around
  FHIR in healthcare. However, efforts are fragmented. There’s a clear opportunity
  to consolidate development around standard, reusable FHIR-based tools not tied to
  any one FHIR server.

- **MCP logic is often tightly coupled:** Today, developers commonly embed MCP logic
  directly into FHIR servers or LLM apps. This results in rigid, non-portable implementations
  that are difficult to reuse or scale.

- **Emerging use cases extend beyond FHIR:** While FHIR remains the primary data
  source for MCP servers, emerging use cases, including clinical trials, research,
  and document search, demand a more flexible and extensible architecture.

Just as apps were decoupled from EHRs via SMART on FHIR, MCP servers must be decoupled
from FHIR servers to enable reusability and ecosystem growth.
