using CommandLine;

namespace MeldRx.Community.PrValidator.Commands;

[Verb(
    "verify-tools-dir",
    HelpText = "Verifies the directory structure of projects and solutions for MCP tools"
)]
public class VerifyDirectoryStructureCommand : ICommand
{
    [Option('c', "changed-files", HelpText = "A list of files that were changed")]
    public IEnumerable<string> ChangedFiles { get; set; } = [];

    [Option(
        'l',
        "language",
        HelpText = "The programming language being used",
        Default = ProgrammingLanguage.Net
    )]
    public ProgrammingLanguage Language { get; set; } = ProgrammingLanguage.Net;
}

public class VerifyDirectoryStructureCommandHandler
    : ICommandHandler<VerifyDirectoryStructureCommand>
{
    public Task<bool> HandleAsync(VerifyDirectoryStructureCommand command)
    {
        var files = command.ChangedFiles.ToList();
        if (files.Count == 0)
        {
            return Task.FromResult(true);
        }

        var hasErrors = false;
        foreach (var file in files)
        {
            if (file.StartsWith(DirectoryNames.GitHub))
            {
                continue;
            }

            if (ContainsInvalidFile(command.Language, file))
            {
                hasErrors = true;
                continue;
            }

            if (!FileExistsInToolsDirectory(command.Language, file))
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: When working with the default MCP server, all files must exist in the /{DirectoryNames.DotnetMcpToolsProject} "
                        + $"directory. Detected file with error: {file}"
                );

                hasErrors = true;
            }
        }

        return Task.FromResult(!hasErrors);
    }

    private bool ContainsInvalidFile(ProgrammingLanguage language, string file)
    {
        if (language == ProgrammingLanguage.Net)
        {
            if (
                file.Contains(".csproj", StringComparison.InvariantCultureIgnoreCase)
                || file.Contains(".sln", StringComparison.InvariantCultureIgnoreCase)
            )
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: Cannot contain project or solution files for default MCP server. Detected file with error: {file}"
                );

                return false;
            }
        }
        else
        {
            if (
                file.Contains("package.json", StringComparison.InvariantCultureIgnoreCase)
                || file.Contains("package-lock.json", StringComparison.InvariantCultureIgnoreCase)
            )
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: Cannot contain package files for default MCP server. Detected file with error: {file}"
                );

                return false;
            }
        }

        return true;
    }

    private bool FileExistsInToolsDirectory(ProgrammingLanguage language, string file)
    {
        if (
            language == ProgrammingLanguage.Net
            && !file.StartsWith($"{DirectoryNames.AbsoluteDotnetMcpToolsProject}/")
        )
        {
            ConsoleUtilities.WriteErrorLine(
                $"ERROR: When working with the default MCP server, all files must exist in the /{DirectoryNames.AbsoluteDotnetMcpToolsProject} "
                    + $"directory. Detected file with error: {file}"
            );

            return false;
        }

        if (
            language == ProgrammingLanguage.Typescript
            && !file.StartsWith($"{DirectoryNames.AbsoluteTypescriptMcpTools}/")
        )
        {
            ConsoleUtilities.WriteErrorLine(
                $"ERROR: When working with the default MCP server, all files must exist in the /{DirectoryNames.AbsoluteTypescriptMcpTools} "
                    + $"directory. Detected file with error: {file}"
            );

            return false;
        }

        return true;
    }
}
