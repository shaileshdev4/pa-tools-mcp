# Terminology

## Agent (Client + Host)

In MCP:

- The **client** is the software entity that connects to the MCP server to receive
  context and tools.

- The **host** is the environment that provides that context, typically an application
  or orchestration layer that knows the patient, user, and FHIR server.

In many practical implementations, **the host and client are in the same system**,
or at least tightly coupled. For clarity and simplicity, SHARP refers to this unified
role as the agent, the logical entity that initiates an MCP session and consumes
its output.

## MCP Server

A remote server that implements the Model Context Protocol and is responsible for:

- Providing **tool definitions**
- Accepting **context inputs**
- Streaming results back to the agent

SHARP on MCP will define best practices and a standard structure for building these
servers in a decoupled, reusable way for healthcare.

## Context

A structured set of parameters that describe the environment, data sources, patient,
and user identity relevant to a particular request.

In SHARP on MCP, **context is typically passed via HTTP headers** (e.g., X-FHIR-Server,
X-Patient-ID, X-Access-Token).

## Tool

A callable function or API exposed by the MCP server that an agent can invoke as
part of its reasoning. Tools include metadata (e.g., name, parameters, return types)
that the agent can use to determine how and when to call them.

## Invocation

The process by which a host or agent sends a request to an MCP server, including
context, and receives streamed output and tool definitions.

## SSE/Streamable HTTP

_TODO_ - [Transports - Model Context Protocol](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)

## FHIR Server

A standards-based data source conforming to HL7 FHIR, commonly used in healthcare
environments to store and access clinical data. MCP servers following SHARP on MCP
are designed to plug into any FHIR-compliant system.

## LLM (Large Language Model)

_TODO_
