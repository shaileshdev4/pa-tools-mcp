using Duende.IdentityServer.EntityFramework.Entities;
using Duende.IdentityServer.EntityFramework.Extensions;
using Duende.IdentityServer.EntityFramework.Interfaces;
using Duende.IdentityServer.EntityFramework.Options;
using Microsoft.EntityFrameworkCore;

namespace MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Database;

public class ApplicationDbContext(
    DbContextOptions<ApplicationDbContext> options,
    ConfigurationStoreOptions configStoreOptions,
    OperationalStoreOptions operationalStoreOptions
) : DbContext(options), IConfigurationDbContext, IPersistedGrantDbContext
{
    public DbSet<Client> Clients { get; set; }

    public DbSet<ClientCorsOrigin> ClientCorsOrigins { get; set; }

    public DbSet<IdentityResource> IdentityResources { get; set; }

    public DbSet<ApiResource> ApiResources { get; set; }

    public DbSet<ApiScope> ApiScopes { get; set; }

    public DbSet<IdentityProvider> IdentityProviders { get; set; }

    public DbSet<PersistedGrant> PersistedGrants { get; set; }

    public DbSet<DeviceFlowCodes> DeviceFlowCodes { get; set; }

    public DbSet<Key> Keys { get; set; }

    public DbSet<ServerSideSession> ServerSideSessions { get; set; }

    public DbSet<PushedAuthorizationRequest> PushedAuthorizationRequests { get; set; }

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ConfigureClientContext(configStoreOptions);
        modelBuilder.ConfigureResourcesContext(configStoreOptions);
        modelBuilder.ConfigureIdentityProviderContext(configStoreOptions);
        modelBuilder.ConfigurePersistedGrantContext(operationalStoreOptions);

        base.OnModelCreating(modelBuilder);
    }
}
