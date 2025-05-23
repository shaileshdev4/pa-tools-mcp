# Contributing MCP Servers

## Overview

You can contribute open source MCP servers in this directory. These servers will
then be available for developers to use and be available as a pluggable MCP server
in the MeldRx ecosystem.

## Helpful Links

- [MCP Specification](https://modelcontextprotocol.io/specification/2025-03-26)
- [MCP Typescript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [Example Dockerfile](darena-solutions/fhir-crud/Dockerfile)
- [Example MCP Server](darena-solutions/fhir-crud)
- [Prettier Formatter](https://prettier.io/)
- [Prettier IDE Setup](https://prettier.io/docs/editors)

## Restrictions

- In the `/servers` directory, create a folder that represents you as an individual
  or an organization. For example `/servers/darena-solutions`.
- Create an additional directory with a project within the previously created directory
  for each MCP server you'd like to build. (EG: `/servers/darena-solutions/fhir-crud`, `/servers/darena-solutions/patient-encounter`).
- The directory that contains your MCP server should be alpha-numeric only. Dashes
  are also allowed. The directory name cannot exceed 16 characters.
- Ensure that you have a `GET /hello-world` endpoint. This will be used to verify
  connectivity to your MCP server. The endpoint should return a 2xx successful code.

### Dockerfile

You must have a `Dockerfile` for your project that we can use to build and deploy
your application. This file must exist at the root of your project (the same directory
as the `package.json` file).

We will run the following command against your Dockerfile:

`docker build -t McpServer .`

We will then run it with:

`docker run --name McpServerContainer -p 3056:5000 McpServer:latest`

Ensure the Dockerfile can build your project and have the project run on port `5000`
inside the container.

- [Example Dockerfile](darena-solutions/fhir-crud/Dockerfile)

### MCP Server Verification

On your PR, we will perform a small verification to ensure the MCP server returns
tool information. We will establish a connection to the MCP server and make a [tools/list](https://modelcontextprotocol.io/specification/2025-03-26/server/tools#listing-tools) call.
Your MCP server should return at least one tool.

The MCP server should not require authentication for us to perform this verification.
If authentication is required, one option is to allow an open request when in the
`development` environment, but require authentication in other environments. Our
process will set the `NODE_ENV` environment variable to `development` when performing
this verification.

We make a StreamableHttp connection to your server (not SSE). Your MCP endpoint
should be at the root level and should not be in separate path.

- Correct: `http://localhost:5000`
- Incorrect: `http://localhost:5000/my_path`

Additionally, ensure you have a `GET /hello-world` endpoint at the root level. This
endpoint will be called initially to ensure connectivity before the MCP connection
is made.

### README

Ensure you have a README located in `/servers/{your directory}/{your server project}/README.md`
for each MCP server. The README should describe the MCP server and its purpose.
It is also a great idea to highlight how to run the MCP server locally and any configurability
provided.

## Pull Requests

Once you are ready with your project, you can create a PR to the main branch. Several
github workflows will begin ensuring that your submission follows the restrictions.
A DarenaSolutions maintainer will review your PR. Once any comments or changes have
been resolved and the PR has been approved, you may merge your changes.

The merge will trigger an action that will make your server available as a pluggable
MCP server in the MeldRx ecosystem.

## Example Project

An example project has been added for reference: [Example Project](darena-solutions/fhir-crud)
