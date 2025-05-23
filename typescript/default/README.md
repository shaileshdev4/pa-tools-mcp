# Contributing to the Default Typescript Server

## Overview

You can contribute to the default typescript MCP server in this directory. Contribution
is limited to creating tools in the `/tools` directory and modifications outside
of this directory are not allowed.

The default MCP server uses [express](https://expressjs.com/) as its web framework.

If you require more control over your MCP server with your own npm packages and
your own programming rules, consider [creating your own MCP server](../servers) instead
of contributing to the default MCP server.

## Restrictions

- In the `/tools` directory, create a directory that represents you as an individual
  or an organization. For example `/tools/darena-solutions`.
- Add your tools and any additional code that your tool requires to run.
- All MCP tools in the directory must be a class that implements the `IMcpTool`
  interface located in `/IMcpTool.ts`.
- The class then needs to be instantiated and exported as a constant. For example:

```typescript
class PatientAgeTool implements IMcpTool {
  registerTool(server: McpServer, req: Request) {}
}

export const PatientAgeToolInstance = new PatientAgeTool();
```

- Update `/tools/index.ts` to re-export this constant. For example:

```typescript
// index.ts
import { PatientAgeToolInstance } from "./darena-solutions/PatientAgeTool";

export { PatientAgeToolInstance };
```

### Formatting

This repository uses [prettier](https://prettier.io/) for formatting. Set this up
in your IDE and ensure your code is formatted before creating a PR.

### Package Dependencies

You are limited to the packages listed in `package.json` and you cannot install
additional packages. If you require an additional package that is not listed there,
contact us and we will review the package and make a determination.

[Creating your own MCP server](../servers) is also an option which does not have
this limitation.

## Pull Requests

Once you are ready with your project, you can create a PR to the main branch. Several
github workflows will begin ensuring that your submission follows the restrictions.
A Darena Solutions maintainer will review your PR. Once any comments or changes
have been resolved and the PR has been approved, you may merge your changes.
