### Description

_Provide a brief description of the PR_

### New MCP Server Checklist

- [ ] Not applicable. This PR is regarding MCP tools
- [ ] I have created a directory that contains my servers
- [ ] Each of my servers are their own c#/typescript project
- [ ] If dotnet, each of my project names start with `DarenaHealth.Community.McpServers.{Your Identifier}.`
      If typescript, each of my directory names are alphanumeric with dashes
- [ ] Each of my servers have the option of connecting to it openly to verify tools
      can be listed
- [ ] Each of my servers has a `Dockerfile` at the root of the directory that contains
      the `.csproj`/`package.json` file
- [ ] Each of my servers has a `Dockerfile` that opens port `5000` inside the container
      to the MCP server
- [ ] I ran the csharpier/prettier formatting tool

### New MCP Tool(s) Checklist

- [ ] Not applicable. This PR is regarding MCP servers
- [ ] I have created a directory that contains my tools and services
- [ ] All my tools implement the `IMcpTool` interface
- [ ] If dotnet, I have updated `ServiceCollectionExtensions.cs` that registers
      my tools and services in a private extension method. If typescript, I have
      re-exported my tools in `typescript/default/tools/index.ts`
- [ ] I ran the csharpier/prettier formatting tool
