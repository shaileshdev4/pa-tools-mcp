using MeldRx.Community.Mcp.Core;
using MeldRx.Community.McpServers.DarenaSolutions.FhirCrud;
using MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Extensions;
using MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Services;
using MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.Tools;
using Microsoft.Extensions.Options;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var mcpToolTypes = typeof(FindPatientIdTool)
    .Assembly.GetTypes()
    .Where(x => !x.IsInterface && x.IsAssignableTo(typeof(IMcpTool)));

foreach (var mcpToolType in mcpToolTypes)
{
    builder.Services.AddScoped(typeof(IMcpTool), mcpToolType);
}

builder
    .Services.AddHttpContextAccessor()
    .AddMcpServer()
    .WithHttpTransport(options => options.Stateless = true)
    .WithListToolsHandler(McpClientListToolsService.Handler)
    .WithCallToolHandler(McpClientCallToolService.Handler);

var applicationSettings = builder
    .Configuration.GetSection(nameof(ApplicationSettings))
    .Get<ApplicationSettings>();

if (applicationSettings is null)
{
    throw new InvalidOperationException("Application settings were not found.");
}

builder.Services.AddSingleton(Options.Create(applicationSettings));
if (applicationSettings.UseIdentityServerAuthentication)
{
    builder.Services.AddDatabaseServices(applicationSettings).AddAuthenticationServices();
}

var app = builder.Build();

if (applicationSettings is { UseIdentityServerAuthentication: true, MigrateDatabase: true })
{
    await app.MigrateAndInitializeDbAsync();
}

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

if (applicationSettings.UseIdentityServerAuthentication)
{
    app.UseIdentityServer();
    app.UseAuthorization();
    app.MapMcp().RequireAuthorization();
}
else
{
    app.MapMcp();
}

app.MapGet("/hello-world", () => $"Hello World! Current time is: {DateTime.UtcNow:O}");

app.Run();
