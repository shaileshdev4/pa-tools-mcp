# SHARP on MCP

While the scope of this effort will expand over time, our initial release focuses
on defining an open-source specification and framework for building MCP servers
that can be plugged into any FHIR server.

It is designed for remote, server-hosted execution, using HTTP+SSE/Streamable HTTP
for communication. We do not include stdio execution. This aligns with “Remote"
in SHARP.

While FHIR is the primary initial use case, the specification is intentionally extensible
and supports integration with other healthcare and research data sources.

Inspired by the principles behind SMART on FHIR and CDS Hooks, the SHARP on MCP
initiative includes:

- A draft specification
- MCP Server templates in multiple programming languages
- A testing harness provided by MeldRx

Together, these components will help developers rapidly build, validate, and deploy
modular MCP servers supporting a wide range of LLM-driven applications across healthcare.
