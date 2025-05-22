FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY /publish ./

ENV ASPNETCORE_URLS=http://*:5000
ENTRYPOINT ["dotnet", "MeldRx.Community.McpServers.DarenaSolutions.FhirCrud.dll"]
