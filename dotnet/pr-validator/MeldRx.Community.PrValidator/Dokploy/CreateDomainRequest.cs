namespace MeldRx.Community.PrValidator.Dokploy;

public class CreateDomainRequest
{
    public required string ApplicationId { get; set; }

    public required string Host { get; set; }

    public string Path { get; set; } = "/";

    public int? Port { get; set; }

    public bool Https { get; set; }

    public string CertificateType { get; set; } = "letsencrypt";

    public string DomainType { get; set; } = "application";
}
