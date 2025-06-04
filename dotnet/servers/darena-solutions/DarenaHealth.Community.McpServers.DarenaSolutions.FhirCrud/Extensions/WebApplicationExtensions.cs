using DarenaHealth.Community.McpServers.DarenaSolutions.FhirCrud.Database;
using Duende.IdentityServer.EntityFramework.Mappers;
using Duende.IdentityServer.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace DarenaHealth.Community.McpServers.DarenaSolutions.FhirCrud.Extensions;

public static class WebApplicationExtensions
{
    private const string McpServerScopeName = "mcp_server";

    public static async Task MigrateAndInitializeDbAsync(this WebApplication app)
    {
        app.Logger.LogInformation("Migrating database...");
        await using var scope = app.Services.CreateAsyncScope();

        var settings = scope
            .ServiceProvider.GetRequiredService<IOptions<ApplicationSettings>>()
            .Value;

        var dbContext = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
        await dbContext.Database.MigrateAsync();

        app.Logger.LogInformation("Database successfully migrated. Seeding scopes...");

        var apiScope = new ApiScope(McpServerScopeName);
        var apiScopeExists = await dbContext.ApiScopes.AnyAsync(x => x.Name == McpServerScopeName);
        if (!apiScopeExists)
        {
            dbContext.ApiScopes.Add(apiScope.ToEntity());
            await dbContext.SaveChangesAsync();
        }

        app.Logger.LogInformation("Scopes successfully seeded. Seeding clients...");

        var defaultClientIds = settings.DefaultClients.Select(x => x.ClientId).ToList();
        var existingDefaultClientIds = await dbContext
            .Clients.Where(x => defaultClientIds.Contains(x.ClientId))
            .Select(x => x.ClientId)
            .ToListAsync();

        var existingDefaultClientsSet = new HashSet<string>(existingDefaultClientIds);
        foreach (var client in settings.DefaultClients)
        {
            if (existingDefaultClientsSet.Contains(client.ClientId))
            {
                continue;
            }

            foreach (var secret in client.ClientSecrets)
            {
                secret.Value = secret.Value.Sha256();
            }

            dbContext.Clients.Add(client.ToEntity());
        }

        await dbContext.SaveChangesAsync();

        app.Logger.LogInformation("Database successfully seeded.");
    }
}
