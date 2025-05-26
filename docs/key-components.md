# 3 Key Components of SHARP on MCP

## 1. MCP Server Authentication

The SHARP on MCP specification defines multiple authentication models that MCP servers
may implement to support both open innovation and enterprise use cases. These mechanisms
enable a range of deployment patterns, from public, community-contributed MCP servers
to private, monetized services with controlled access.

The MCP server must support one or more of the following methods to allow agents
to connect:

-   **Anonymous access:** The MCP server does not require the client to authenticate
    at the connection level. However, this does not imply unrestricted use. For example,
    the server may still require context parameters such as FHIR Server URL, Access
    Token, or Patient ID in the request headers to function correctly.

-   **OAuth Client Credentials:** The MCP server supports authenticating the client
    using the [client credentials grant](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-12#name-client-credentials-grant).

    -   Clients may register with the MCP authorization server using dynamic registration.

-   **API-key based access:** LLM apps authenticate with MCP servers via API keys.

-   **Basic authentication:** LLM apps authenticate with MCP servers using a username
    and password. The username and password are first combined in this format: `{username}:{password}`.
    This value is then base64 encoded and sent as a header: `Authorization: Basic {base64EncodedValue}`.

These flexible authentication models allow developers and vendors to choose the
security, governance, and commercialization level that best fits their use case.
Whether enabling **open-access public MCP servers** or supporting **enterprise-grade
monetization and contractual control**, SHARP on MCP provides a standards-based
foundation for interoperable, agent-ready services.

## 2.Context Passing (The "Hooks" Layer)

In SMART on FHIR, there are two main ways to authenticate. In the standalone and
EHR launch, users authenticate in-session. For backend flows, the client is authenticated
using client credentials. For SHARP on MCP, we assume that the Agent is already
authenticated by one of these flows (or another way) before connecting to the
MCP server. Hence, repeating a SMART on FHIR flow is inappropriate.

Therefore, we propose a **CDS Hooks-style context delivery method** via **HTTP headers**,
allowing calling apps to provide the necessary execution context directly to the
MCP server.

**Proposed Header Schema (initial draft):**

-   `X-FHIR-Server-URL`
-   `X-FHIR-Access-Token`
-   `X-Patient-ID`
-   `X-User-ID`
-   `X-Tenant-ID`
-   `X-Context-Version`

We welcome contributions from the community to help **refine and further standardize
the context headers** used in SHARP on MCP.

The current set of headers assumes that the **MCP server will connect to an FHIR
backend. However, these may vary depending on the MCP server's specific capabilities
and purpose**. As such, the specification is intentionally flexible to accommodate
different use cases.

In the case of FHIR-backed servers, the **FHIR access token** plays a central role:
It determines the **scope of permissions** granted to the MCP server. The agent
(or host) must acquire or construct this token with the appropriate scopes and deliver
it to the MCP server as part of the request, mirroring the **authorization model
used in CDS Hooks**.

## 3. FHIR Context Discovery

MCP servers will have a mechanism to advertise to agents the level of access they
require. The FHIR-based MCP server will share the scopes of the tools that need
to be used. We are building on top of the MCP discovery document as specified in
the [MCP specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization#2-3-server-metadata-discovery).

In addition to the base discovery document, we are adding some additional properties:

-   `fhir_context_required` – A Boolean value indicating whether FHIR context is required.
    If FHIR context is required, the client is required to include the `X-FHIR-Server-URL`,
    `X-FHIR-Access-Token`, and (optionally) `X-Patient-ID` headers.

    -   If FHIR context is required and the client does not include one or more of the
        required headers, the MCP server should respond with a 403 Forbidden response.

-   `fhir_tools` – An array of FHIR tools that require FHIR context. Each object in
    the array will contain the tool name and an array of scopes that are required to
    be able to use that tool.

    -   `fhir_tools.name` - The name of the tool that requires FHIR context.
    -   `fhir_tools.scopes` - An array of SMART-on-FHIR scopes required to use this tool.
    -   If the MCP server has a FHIR tool and the client provides an access token in
        the `X-FHIR-Access-Token` header that does not contain all the scopes required,
        the MCP server SHOULD exclude the tool in the [tools/list](https://modelcontextprotocol.io/specification/2025-03-26/server/tools#listing-tools)
        endpoint.

Here is an example discovery document returned from /.well-known/oauth-authorization-server.
_TODO_

This discovery document indicates that FHIR context is required, and the client
must include the `X-FHIR-Server-URL`, `X-FHIR-Access-Token`, and `X-Patient-ID`
headers. It also indicates that it has two FHIR tools, `read_fhir_resource` which
requires the `patient/*.read` scope, and `create_fhir_resource` which requires the
`patient/.write` scope.

In this example, if a client were to provide an access token that only contains
a `patient/*.read` scope, then the client can only use the `read_fhir_resource`
tool. This will be restricted by the MCP server by excluding the `create_fhir_resource`
tool in the [tools/list](https://modelcontextprotocol.io/specification/2025-03-26/server/tools#listing-tools)
endpoint.
