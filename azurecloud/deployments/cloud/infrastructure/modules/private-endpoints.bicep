// =============================================================================
// Private Endpoints Module
// =============================================================================

@description('Azure region')
param location string

@description('Resource prefix')
param resourcePrefix string

@description('VNet ID')
param vnetId string

@description('Private endpoint subnet ID')
param subnetId string

@description('Azure OpenAI resource ID')
param openaiId string

@description('Azure Search resource ID')
param searchId string

@description('Cosmos DB resource ID')
param cosmosId string

@description('Storage Account resource ID')
param storageId string

@description('Key Vault resource ID')
param keyVaultId string

@description('Tags')
param tags object

// =============================================================================
// Private DNS Zone References
// =============================================================================

resource openaiDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.openai.azure.com'
}

resource searchDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.search.windows.net'
}

resource cosmosDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.documents.azure.com'
}

resource blobDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.blob.${az.environment().suffixes.storage}'
}

resource keyVaultDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: 'privatelink.vaultcore.azure.net'
}

// =============================================================================
// Azure OpenAI Private Endpoint
// =============================================================================

resource openaiPe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${resourcePrefix}-openai'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'openai-connection'
        properties: {
          privateLinkServiceId: openaiId
          groupIds: ['account']
        }
      }
    ]
  }
}

resource openaiPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: openaiPe
  name: 'dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai-dns'
        properties: {
          privateDnsZoneId: openaiDnsZone.id
        }
      }
    ]
  }
}

// =============================================================================
// Azure Search Private Endpoint
// =============================================================================

resource searchPe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${resourcePrefix}-search'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'search-connection'
        properties: {
          privateLinkServiceId: searchId
          groupIds: ['searchService']
        }
      }
    ]
  }
}

resource searchPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: searchPe
  name: 'dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'search-dns'
        properties: {
          privateDnsZoneId: searchDnsZone.id
        }
      }
    ]
  }
}

// =============================================================================
// Cosmos DB Private Endpoint
// =============================================================================

resource cosmosPe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${resourcePrefix}-cosmos'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'cosmos-connection'
        properties: {
          privateLinkServiceId: cosmosId
          groupIds: ['Sql']
        }
      }
    ]
  }
}

resource cosmosPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: cosmosPe
  name: 'dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos-dns'
        properties: {
          privateDnsZoneId: cosmosDnsZone.id
        }
      }
    ]
  }
}

// =============================================================================
// Storage Blob Private Endpoint
// =============================================================================

resource storagePe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${resourcePrefix}-blob'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'blob-connection'
        properties: {
          privateLinkServiceId: storageId
          groupIds: ['blob']
        }
      }
    ]
  }
}

resource storagePeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: storagePe
  name: 'dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob-dns'
        properties: {
          privateDnsZoneId: blobDnsZone.id
        }
      }
    ]
  }
}

// =============================================================================
// Key Vault Private Endpoint
// =============================================================================

resource keyVaultPe 'Microsoft.Network/privateEndpoints@2023-09-01' = {
  name: 'pe-${resourcePrefix}-keyvault'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'keyvault-connection'
        properties: {
          privateLinkServiceId: keyVaultId
          groupIds: ['vault']
        }
      }
    ]
  }
}

resource keyVaultPeDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-09-01' = {
  parent: keyVaultPe
  name: 'dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'keyvault-dns'
        properties: {
          privateDnsZoneId: keyVaultDnsZone.id
        }
      }
    ]
  }
}

// =============================================================================
// Outputs
// =============================================================================

output openaiPrivateEndpointId string = openaiPe.id
output searchPrivateEndpointId string = searchPe.id
output cosmosPrivateEndpointId string = cosmosPe.id
output storagePrivateEndpointId string = storagePe.id
output keyVaultPrivateEndpointId string = keyVaultPe.id
