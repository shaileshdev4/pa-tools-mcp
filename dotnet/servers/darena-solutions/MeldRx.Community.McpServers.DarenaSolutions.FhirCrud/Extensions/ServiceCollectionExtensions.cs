using MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Database;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;

namespace MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Extensions;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddDatabaseServices(
        this IServiceCollection services,
        ApplicationSettings settings
    )
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(settings.DatabaseConStr);

        return services.AddDbContext<ApplicationDbContext>(options =>
            options.UseNpgsql(settings.DatabaseConStr)
        );
    }

    public static IServiceCollection AddAuthenticationServices(this IServiceCollection services)
    {
        services
            .AddIdentityServer()
            .AddConfigurationStore<ApplicationDbContext>()
            .AddOperationalStore<ApplicationDbContext>();

        services
            .AddAuthentication(options =>
            {
                options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
                options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
            })
            .AddJwtBearer(options =>
            {
                options.Authority = "https://localhost:7013";
                options.TokenValidationParameters.ValidateAudience = false;
            });

        return services.AddAuthorization();
    }
}
