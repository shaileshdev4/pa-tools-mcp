# Introduction & Vision

We’re excited to share an open-source initiative to define a standardized protocol
for AI agents to communicate with external (remote), server-based healthcare services.
Whether used for summarization, data extraction, clinical guidance, or automation,
these services need a consistent and interoperable interface to connect with healthcare
data using FHIR or beyond. SHARP (Standardized Healthcare Agent Remote Protocol)
is a specification designed to fill that gap.

SHARP on MCP is the initial release built on the existing Model Context Protocol
(MCP), currently the most widely (and only) adopted standard for enabling agents
to access data through tools. SHARP on MCP aims to serve as a foundational layer
for pluggable, composable, and interoperable agent-facing services based on the
MCP specifications. However, SHARP may evolve to support additional protocols in
the future.

We aim to create what SMART on FHIR did for EHR applications, but for MCP server-like
services: a universal, reusable architecture that allows MCP servers to be independently
developed, hosted, and integrated with any FHIR server or other healthcare systems
and databases.
