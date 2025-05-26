using System.Reflection;

namespace MeldRx.Community.PrValidator;

public static class FileUtilities
{
    public static string GetRepoRootDirectory()
    {
        var githubWorkspaceDir = Environment.GetEnvironmentVariable("GITHUB_WORKSPACE");
        if (!string.IsNullOrWhiteSpace(githubWorkspaceDir))
        {
            return githubWorkspaceDir;
        }

        var executingDirectory =
            Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)
            ?? throw new InvalidOperationException(
                "Could not find the executing assembly location"
            );

        var currentDir = new DirectoryInfo(executingDirectory);
        while (currentDir.EnumerateDirectories().All(x => x.Name != DirectoryNames.GitHub))
        {
            currentDir =
                currentDir.Parent
                ?? throw new InvalidOperationException("Could not find root repository directory.");
        }

        return currentDir.FullName;
    }

    public static bool TryGetProjectDirectories(
        List<string> changedFiles,
        out List<string> projectDirectories
    )
    {
        projectDirectories = [];
        var directoriesChecked = new HashSet<string>();
        var rootDirectory = GetRepoRootDirectory();

        foreach (var file in changedFiles)
        {
            var fi = new FileInfo(Path.Combine(rootDirectory, file));
            if (fi.Directory is null)
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: The following file is not contained in a directory: {file}"
                );

                return false;
            }

            if (!directoriesChecked.Add(fi.Directory.FullName))
            {
                continue;
            }

            if (
                !TryFindProjectDirectory(
                    file.StartsWith(DirectoryNames.Dotnet)
                        ? ProgrammingLanguage.Net
                        : ProgrammingLanguage.Typescript,
                    fi.Directory,
                    file,
                    out var projectDi
                ) || projectDi is null
            )
            {
                return false;
            }

            projectDirectories.Add(projectDi.FullName);
            directoriesChecked.Add(projectDi.FullName);
        }

        return true;
    }

    private static bool TryFindProjectDirectory(
        ProgrammingLanguage language,
        DirectoryInfo di,
        string startFile,
        out DirectoryInfo? projectDi
    )
    {
        projectDi = null;
        while (true)
        {
            string? projectFile = null;
            string? dockerFile = null;
            foreach (var fi in di.EnumerateFiles())
            {
                if (
                    language == ProgrammingLanguage.Net
                    && string.Equals(
                        ".csproj",
                        fi.Extension,
                        StringComparison.InvariantCultureIgnoreCase
                    )
                )
                {
                    projectFile = fi.FullName;
                }

                if (
                    language == ProgrammingLanguage.Typescript
                    && string.Equals(
                        "package.json",
                        fi.Name,
                        StringComparison.InvariantCultureIgnoreCase
                    )
                )
                {
                    projectFile = fi.FullName;
                }

                if (
                    string.Equals(
                        "dockerfile",
                        fi.Name,
                        StringComparison.InvariantCultureIgnoreCase
                    )
                )
                {
                    dockerFile = fi.FullName;
                }
            }

            if (string.IsNullOrWhiteSpace(projectFile))
            {
                if (di.Parent is null)
                {
                    ConsoleUtilities.WriteErrorLine(
                        $"ERROR: Could not find the project directory for file: {startFile}"
                    );

                    return false;
                }

                di = di.Parent;
                continue;
            }

            if (string.IsNullOrWhiteSpace(dockerFile))
            {
                ConsoleUtilities.WriteErrorLine(
                    $"ERROR: Could not find docker file in project directory: {di.FullName}"
                );

                return false;
            }

            projectDi = di;
            return true;
        }
    }
}
