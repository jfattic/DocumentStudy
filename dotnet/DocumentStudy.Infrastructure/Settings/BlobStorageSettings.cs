using System.ComponentModel.DataAnnotations;

namespace DocumentStudy.Infrastructure.Settings;

public class BlobStorageSettings
{
    [Required]
    public string ConnectionString { get; set; } = string.Empty;

    [Required]
    public string RawContainer { get; set; } = string.Empty;

    [Required]
    public string CookedContainer { get; set; } = string.Empty;
}
