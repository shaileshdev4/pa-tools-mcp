# Overview

An open source repository where developers can create MCP servers and/or tools in
the healthcare space.

MCP servers and tools may be requested by a member from Darena Solutions or another
member of the community. These requests can also have bounties which then get rewarded
to the developer that successfully merges and implements the requested feature.

## SHARP-on-MCP Specification

- [latest version](https://www.sharponmcp.com/)

## Default MCP Server Vs. Creating Your Own

There is a default MCP server in this repoistory for both dotnet and typescript.
These MCP servers are available in the DarenaHealth workspace ecosystem. Contributors
can only contribute additional tools to this MCP server but cannot make any modifications
outside of tools at this time. The default servers will be reviewed more critically
as it is included in a key part of our product.

Contributors can also create their own MCP servers. Restrictions are more lax using
this option as developers are allowed to build their MCP server using any package
they require and using any structure. We will ultimately test your final packaged
MCP server to ensure connectivity when you create your own MCP server.

# Contributing

- DotNet
  - [Create an MCP Server](dotnet/servers)
  - [Contributing to the Default MCP Server](dotnet/default)
- Typescript
  - [Create an MCP Server](typescript/servers)
  - [Contributing to the Default MCP Server](typescript/default)
