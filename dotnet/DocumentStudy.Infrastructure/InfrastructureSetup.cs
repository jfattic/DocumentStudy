using Azure.AI.DocumentIntelligence;
using Azure.Core.Pipeline;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;
using DocumentStudy.Infrastructure.Settings;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.ChatCompletion;
using Microsoft.SemanticKernel.Connectors.AzureOpenAI;

namespace DocumentStudy.Infrastructure;

public static class InfrastructureSetup
{
    public static IServiceCollection AddInfrastructureServices
        (this IServiceCollection services, IConfiguration config)
    {
        AddAIServices(services, config);

        AddDocumentIntelligence(services, config);

        AddBlobStorageClients(services, config);

        return services;
    }

    private static void AddAIServices
        (IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<AISettings>()
                .Bind(config.GetSection("AzureOpenAI"))
                .ValidateDataAnnotations()
                .ValidateOnStart();

        services.AddSingleton<IChatCompletionService>(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<AISettings>>().Value;
            return new AzureOpenAIChatCompletionService(
                settings.ChatDeploymentName, settings.Endpoint, settings.ApiKey);
        });

        services.AddTransient<Kernel>(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<AISettings>>().Value;
            var chatService = sp.GetRequiredService<IChatCompletionService>();
            var builder = Kernel.CreateBuilder();
            builder.Services.AddSingleton(chatService);

#pragma warning disable SKEXP0010 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
            builder.Services.AddAzureOpenAIEmbeddingGenerator(
                deploymentName: settings.EmbeddingDeploymentName,
                endpoint: settings.Endpoint,
                apiKey: settings.ApiKey,
                dimensions: settings.EmbeddingVectorDimensions);
#pragma warning restore SKEXP0010 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.

            return builder.Build();
        });
    }

    private static void AddDocumentIntelligence(IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<DocumentIntelligenceSettings>()
                .Bind(config.GetSection("DocumentIntelligence"))
                .ValidateDataAnnotations()
                .ValidateOnStart();

        services.AddSingleton<DocumentIntelligenceClient>(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<DocumentIntelligenceSettings>>().Value;

            var clientOptions = new DocumentIntelligenceClientOptions
            {
                Retry =
                {
                    MaxRetries = 3,
                    Delay = TimeSpan.FromSeconds(5),
                    MaxDelay = TimeSpan.FromSeconds(30),
                    Mode = Azure.Core.RetryMode.Exponential
                },
                // configure network timeout for document analysis
                Transport = new HttpClientTransport(new HttpClient()
                {
                    Timeout = TimeSpan.FromMinutes(15) // Document Analysis can take a long time
                })
            };

            return new DocumentIntelligenceClient(
                new Uri(settings.Endpoint),
                new Azure.AzureKeyCredential(settings.ApiKey),
                clientOptions);
        });
    }

    private static void AddBlobStorageClients(IServiceCollection services, IConfiguration config)
    {
        services.AddOptions<BlobStorageSettings>()
                .Bind(config.GetSection("BlobStorage"))
                .ValidateDataAnnotations()
                .ValidateOnStart();

        services.AddSingleton<BlobServiceClient>(sp =>
        {
            var settings = sp.GetRequiredService<IOptions<BlobStorageSettings>>().Value;
            return new BlobServiceClient(settings.ConnectionString);
        });

        services.AddKeyedSingleton<BlobContainerClient>("raw", (sp, _) =>
        {
            var settings = sp.GetRequiredService<IOptions<BlobStorageSettings>>().Value;
            var serviceClient = sp.GetRequiredService<BlobServiceClient>();
            var containerClient = serviceClient.GetBlobContainerClient(settings.RawContainer);
            containerClient.CreateIfNotExists(publicAccessType: PublicAccessType.BlobContainer);
            return containerClient;
        });

        services.AddKeyedSingleton<BlobContainerClient>("cooked", (sp, _) =>
        {
            var settings = sp.GetRequiredService<IOptions<BlobStorageSettings>>().Value;
            var serviceClient = sp.GetRequiredService<BlobServiceClient>();
            var containerClient = serviceClient.GetBlobContainerClient(settings.CookedContainer);
            containerClient.CreateIfNotExists(publicAccessType: PublicAccessType.BlobContainer);
            return containerClient;
        });
    }
}
