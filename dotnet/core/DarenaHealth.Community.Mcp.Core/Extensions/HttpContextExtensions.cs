using System.IdentityModel.Tokens.Jwt;
using DarenaHealth.Community.Mcp.Core.Models;
using Microsoft.AspNetCore.Http;

namespace DarenaHealth.Community.Mcp.Core.Extensions;

public static class HttpContextExtensions
{
    public static FhirContext? GetFhirContext(this HttpContext httpContext)
    {
        var headers = httpContext.Request.Headers;
        if (
            !headers.TryGetValue(SharpOnMcpConstants.FhirServerUrlHeaderName, out var url)
            || string.IsNullOrWhiteSpace(url)
        )
        {
            return null;
        }

        if (
            !headers.TryGetValue(SharpOnMcpConstants.FhirAccessTokenHeaderName, out var token)
            || string.IsNullOrWhiteSpace(token)
        )
        {
            return null;
        }

        return new FhirContext { Url = url!, Token = token! };
    }

    public static string? GetPatientIdIfContextExists(this HttpContext httpContext)
    {
        var fhirToken = httpContext.Request.Headers[SharpOnMcpConstants.FhirAccessTokenHeaderName];
        if (!string.IsNullOrWhiteSpace(fhirToken))
        {
            var handler = new JwtSecurityTokenHandler();
            var jwtToken = handler.ReadJwtToken(fhirToken);
            var patientClaim = jwtToken.Claims.FirstOrDefault(x =>
                string.Equals("patient", x.Type, StringComparison.InvariantCultureIgnoreCase)
            );

            if (patientClaim is not null && !string.IsNullOrWhiteSpace(patientClaim.Value))
            {
                return patientClaim.Value;
            }
        }

        var headerValue = httpContext.Request.Headers[SharpOnMcpConstants.PatientIdHeaderName];
        return !string.IsNullOrWhiteSpace(headerValue) ? headerValue.ToString() : null;
    }
}
