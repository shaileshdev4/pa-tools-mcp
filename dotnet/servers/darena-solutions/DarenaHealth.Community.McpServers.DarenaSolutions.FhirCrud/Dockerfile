FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /source
COPY /core ./core
COPY /servers ./servers
WORKDIR /source/servers/darena-solutions/DarenaHealth.Community.McpServers.DarenaSolutions.FhirCrud
RUN dotnet publish -c Release -r linux-x64 -o /publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /publish ./

ENV ASPNETCORE_URLS=http://*:5000
ENTRYPOINT ["dotnet", "DarenaHealth.Community.McpServers.DarenaSolutions.FhirCrud.dll"]
