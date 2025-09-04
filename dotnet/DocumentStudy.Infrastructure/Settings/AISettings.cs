using System.ComponentModel.DataAnnotations;

namespace DocumentStudy.Infrastructure.Settings;

public class AISettings
{
    [Required]
    public string Endpoint { get; set; } = string.Empty;

    [Required]
    public string ApiKey { get; set; } = string.Empty;

    public string ChatDeploymentName { get; set; } = string.Empty;

    public string EmbeddingDeploymentName { get; set; } = string.Empty;

    public int EmbeddingVectorDimensions { get; set; } = 1536;
}
