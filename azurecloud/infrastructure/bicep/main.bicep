// ============================================================================
// Main Bicep Template for Enterprise RAG Platform
// ============================================================================
//
// This template deploys the complete infrastructure for a multi-modal RAG
// system with:
// - Azure AI Search (vector + hybrid search)
// - Azure OpenAI (embeddings + chat)
// - Document Intelligence
// - Cosmos DB (manifests + graph + cache)
// - Storage (documents + processed data)
// - Functions (ingestion + RAG processing)
// - Private networking (zero-trust)
// - Monitoring and governance
//
// ============================================================================

targetScope = 'resourceGroup'

// ============================================================================
// Parameters
// ============================================================================

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Azure region for deployment')
param location string = resourceGroup().location

@description('Project name prefix for resource naming')
@minLength(3)
@maxLength(10)
param projectName string = 'ragcopilot'

@description('Owner email for tagging')
param ownerEmail string

@description('Cost center for billing')
param costCenter string = 'ai-platform'

@description('Enable private endpoints (zero-trust networking)')
param enablePrivateEndpoints bool = true

@description('VNet address space')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Azure OpenAI model deployments')
param openAIModels array = [
  {
    name: 'gpt-4o'
    model: 'gpt-4o'
    version: '2024-08-06'
    capacity: 40
  }
  {
    name: 'gpt-4o-mini'
    model: 'gpt-4o-mini'
    version: '2024-07-18'
    capacity: 80
  }
  {
    name: 'text-embedding-3-large'
    model: 'text-embedding-3-large'
    version: '1'
    capacity: 120
  }
]

// ============================================================================
// Variables
// ============================================================================

var resourceSuffix = '${projectName}-${environment}-${uniqueString(resourceGroup().id)}'
var tags = {
  Environment: environment
  Project: projectName
  Owner: ownerEmail
  CostCenter: costCenter
  ManagedBy: 'bicep'
}

// Subnet configuration
var subnets = [
  {
    name: 'snet-ai'
    addressPrefix: '10.0.1.0/24'
    serviceEndpoints: ['Microsoft.CognitiveServices', 'Microsoft.Storage']
    delegations: []
  }
  {
    name: 'snet-data'
    addressPrefix: '10.0.2.0/24'
    serviceEndpoints: ['Microsoft.Storage', 'Microsoft.AzureCosmosDB']
    delegations: []
  }
  {
    name: 'snet-compute'
    addressPrefix: '10.0.3.0/24'
    serviceEndpoints: []
    delegations: [
      {
        name: 'delegation-functions'
        properties: {
          serviceName: 'Microsoft.Web/serverFarms'
        }
      }
    ]
  }
  {
    name: 'snet-private-endpoints'
    addressPrefix: '10.0.4.0/24'
    serviceEndpoints: []
    delegations: []
  }
]

// ============================================================================
// Networking
// ============================================================================

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: 'vnet-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    subnets: [for subnet in subnets: {
      name: subnet.name
      properties: {
        addressPrefix: subnet.addressPrefix
        serviceEndpoints: [for endpoint in subnet.serviceEndpoints: {
          service: endpoint
        }]
        delegations: subnet.delegations
        privateEndpointNetworkPolicies: 'Disabled'
      }
    }]
  }
}

// Private DNS Zones
resource privateDnsZoneOpenAI 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateEndpoints) {
  name: 'privatelink.openai.azure.com'
  location: 'global'
  tags: tags
}

resource privateDnsZoneSearch 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateEndpoints) {
  name: 'privatelink.search.windows.net'
  location: 'global'
  tags: tags
}

resource privateDnsZoneCosmos 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateEndpoints) {
  name: 'privatelink.documents.azure.com'
  location: 'global'
  tags: tags
}

resource privateDnsZoneBlob 'Microsoft.Network/privateDnsZones@2020-06-01' = if (enablePrivateEndpoints) {
  name: 'privatelink.blob.core.windows.net'
  location: 'global'
  tags: tags
}

// Link DNS zones to VNet
resource vnetLinkOpenAI 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateEndpoints) {
  parent: privateDnsZoneOpenAI
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkSearch 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateEndpoints) {
  parent: privateDnsZoneSearch
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkCosmos 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateEndpoints) {
  parent: privateDnsZoneCosmos
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource vnetLinkBlob 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (enablePrivateEndpoints) {
  parent: privateDnsZoneBlob
  name: 'link-${vnet.name}'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// ============================================================================
// Storage Account
// ============================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('st${resourceSuffix}', '-', '')
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_GRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    isHnsEnabled: true // Enable hierarchical namespace for ADLS Gen2
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      defaultAction: enablePrivateEndpoints ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
    supportsHttpsTrafficOnly: true
  }
}

// Storage containers
resource containerRaw 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/raw-documents'
  properties: {
    publicAccess: 'None'
  }
}

resource containerProcessed 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/processed-chunks'
  properties: {
    publicAccess: 'None'
  }
}

resource containerFigures 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storageAccount.name}/default/extracted-figures'
  properties: {
    publicAccess: 'None'
  }
}

// ============================================================================
// Azure OpenAI
// ============================================================================

resource openAI 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: 'oai-${resourceSuffix}'
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'oai-${resourceSuffix}'
    publicNetworkAccess: enablePrivateEndpoints ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateEndpoints ? 'Deny' : 'Allow'
    }
  }
}

// Model deployments
resource openAIDeployments 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = [for model in openAIModels: {
  parent: openAI
  name: model.name
  sku: {
    name: 'Standard'
    capacity: model.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: model.model
      version: model.version
    }
    raiPolicyName: 'Microsoft.Default'
  }
}]

// ============================================================================
// Azure AI Search
// ============================================================================

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: 'srch-${resourceSuffix}'
  location: location
  tags: tags
  sku: {
    name: 'standard'
  }
  properties: {
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: environment == 'prod' ? 2 : 1
    publicNetworkAccess: enablePrivateEndpoints ? 'disabled' : 'enabled'
    semanticSearch: 'standard'
  }
}

// ============================================================================
// Document Intelligence
// ============================================================================

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: 'di-${resourceSuffix}'
  location: location
  tags: tags
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'di-${resourceSuffix}'
    publicNetworkAccess: enablePrivateEndpoints ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateEndpoints ? 'Deny' : 'Allow'
    }
  }
}

// ============================================================================
// Cosmos DB
// ============================================================================

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-11-15' = {
  name: 'cosmos-${resourceSuffix}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: environment == 'prod'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    enableAutomaticFailover: environment == 'prod'
    publicNetworkAccess: enablePrivateEndpoints ? 'Disabled' : 'Enabled'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

// Cosmos DB Database
resource cosmosDatabase 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-11-15' = {
  parent: cosmosAccount
  name: 'rag-platform'
  properties: {
    resource: {
      id: 'rag-platform'
    }
  }
}

// Cosmos DB Containers
resource containerManifests 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'document-manifests'
  properties: {
    resource: {
      id: 'document-manifests'
      partitionKey: {
        paths: ['/tenant_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/doc_id/?' }
          { path: '/status/?' }
          { path: '/last_ingested_utc/?' }
        ]
        excludedPaths: [
          { path: '/page_hashes/*' }
          { path: '/"_etag"/?' }
        ]
      }
      defaultTtl: -1
    }
  }
}

resource containerGraphNodes 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'graph-nodes'
  properties: {
    resource: {
      id: 'graph-nodes'
      partitionKey: {
        paths: ['/tenant_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/entity_type/?' }
          { path: '/normalized_name/?' }
        ]
      }
    }
  }
}

resource containerGraphEdges 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'graph-edges'
  properties: {
    resource: {
      id: 'graph-edges'
      partitionKey: {
        paths: ['/tenant_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/source_entity_id/?' }
          { path: '/target_entity_id/?' }
          { path: '/relation_type/?' }
        ]
      }
    }
  }
}

resource containerMemory 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'domain-memory'
  properties: {
    resource: {
      id: 'domain-memory'
      partitionKey: {
        paths: ['/tenant_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        includedPaths: [
          { path: '/fact_type/?' }
          { path: '/confidence/?' }
          { path: '/valid_from/?' }
        ]
      }
    }
  }
}

resource containerAudit 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-11-15' = {
  parent: cosmosDatabase
  name: 'audit-logs'
  properties: {
    resource: {
      id: 'audit-logs'
      partitionKey: {
        paths: ['/tenant_id']
        kind: 'Hash'
      }
      defaultTtl: 7776000 // 90 days
    }
  }
}

// ============================================================================
// Key Vault
// ============================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true
    publicNetworkAccess: enablePrivateEndpoints ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateEndpoints ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
  }
}

// ============================================================================
// Application Insights
// ============================================================================

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 90
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${resourceSuffix}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ============================================================================
// Function App (Ingestion Pipeline)
// ============================================================================

resource functionAppPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: 'asp-func-${resourceSuffix}'
  location: location
  tags: tags
  kind: 'elastic'
  sku: {
    name: 'EP1'
    tier: 'ElasticPremium'
  }
  properties: {
    maximumElasticWorkerCount: 20
    reserved: true // Linux
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: 'func-ingestion-${resourceSuffix}'
  location: location
  tags: tags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionAppPlan.id
    httpsOnly: true
    virtualNetworkSubnetId: enablePrivateEndpoints ? vnet.properties.subnets[2].id : null
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      pythonVersion: '3.11'
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
      appSettings: [
        { name: 'AzureWebJobsStorage', value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};EndpointSuffix=${az.environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}' }
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'python' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsights.properties.ConnectionString }
        { name: 'AZURE_OPENAI_ENDPOINT', value: openAI.properties.endpoint }
        { name: 'AZURE_SEARCH_ENDPOINT', value: 'https://${searchService.name}.search.windows.net' }
        { name: 'COSMOS_ENDPOINT', value: cosmosAccount.properties.documentEndpoint }
        { name: 'DOC_INTELLIGENCE_ENDPOINT', value: documentIntelligence.properties.endpoint }
        { name: 'KEY_VAULT_URI', value: keyVault.properties.vaultUri }
        { name: 'ENVIRONMENT', value: environment }
      ]
    }
  }
}

// ============================================================================
// Private Endpoints
// ============================================================================

resource peOpenAI 'Microsoft.Network/privateEndpoints@2023-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-oai-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[3].id
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-oai'
        properties: {
          privateLinkServiceId: openAI.id
          groupIds: ['account']
        }
      }
    ]
  }
}

resource peSearch 'Microsoft.Network/privateEndpoints@2023-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-srch-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[3].id
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-srch'
        properties: {
          privateLinkServiceId: searchService.id
          groupIds: ['searchService']
        }
      }
    ]
  }
}

resource peCosmos 'Microsoft.Network/privateEndpoints@2023-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-cosmos-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[3].id
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-cosmos'
        properties: {
          privateLinkServiceId: cosmosAccount.id
          groupIds: ['Sql']
        }
      }
    ]
  }
}

resource peStorage 'Microsoft.Network/privateEndpoints@2023-05-01' = if (enablePrivateEndpoints) {
  name: 'pe-st-${resourceSuffix}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[3].id
    }
    privateLinkServiceConnections: [
      {
        name: 'plsc-blob'
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: ['blob']
        }
      }
    ]
  }
}

// DNS Zone Groups for Private Endpoints
resource dnsGroupOpenAI 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = if (enablePrivateEndpoints) {
  parent: peOpenAI
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneOpenAI.id
        }
      }
    ]
  }
}

resource dnsGroupSearch 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = if (enablePrivateEndpoints) {
  parent: peSearch
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneSearch.id
        }
      }
    ]
  }
}

resource dnsGroupCosmos 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = if (enablePrivateEndpoints) {
  parent: peCosmos
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneCosmos.id
        }
      }
    ]
  }
}

resource dnsGroupStorage 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = if (enablePrivateEndpoints) {
  parent: peStorage
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneBlob.id
        }
      }
    ]
  }
}

// ============================================================================
// RBAC Role Assignments
// ============================================================================

// Function App -> OpenAI (Cognitive Services User)
resource roleOpenAI 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, openAI.id, 'CognitiveServicesUser')
  scope: openAI
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Function App -> Search (Search Index Data Contributor)
resource roleSearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, searchService.id, 'SearchIndexDataContributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Function App -> Cosmos (Cosmos DB Data Contributor)
resource roleCosmos 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, cosmosAccount.id, 'DocumentDBAccountContributor')
  scope: cosmosAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5bd9cd88-fe45-4216-938b-f97437e15450')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Function App -> Storage (Storage Blob Data Contributor)
resource roleStorage 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, storageAccount.id, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Function App -> Key Vault (Key Vault Secrets User)
resource roleKeyVault 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionApp.id, keyVault.id, 'KeyVaultSecretsUser')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// ============================================================================
// Outputs
// ============================================================================

output vnetId string = vnet.id
output storageAccountName string = storageAccount.name
output openAIEndpoint string = openAI.properties.endpoint
output searchServiceName string = searchService.name
output cosmosAccountName string = cosmosAccount.name
output functionAppName string = functionApp.name
output keyVaultName string = keyVault.name
output appInsightsConnectionString string = appInsights.properties.ConnectionString
