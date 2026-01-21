// =============================================================================
// Network Module - VNet, Subnets, NSGs
// =============================================================================

@description('Azure region')
param location string

@description('Resource prefix')
param resourcePrefix string

@description('Tags')
param tags object

// =============================================================================
// Variables
// =============================================================================

var vnetName = 'vnet-${resourcePrefix}'
var vnetAddressPrefix = '10.0.0.0/16'

var subnets = {
  functions: {
    name: 'snet-functions'
    addressPrefix: '10.0.1.0/24'
  }
  privateEndpoints: {
    name: 'snet-private-endpoints'
    addressPrefix: '10.0.2.0/24'
  }
  integration: {
    name: 'snet-integration'
    addressPrefix: '10.0.3.0/24'
  }
}

// =============================================================================
// Network Security Groups
// =============================================================================

resource functionsNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'nsg-${subnets.functions.name}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPS'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

resource privateEndpointsNsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: 'nsg-${subnets.privateEndpoints.name}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowVNetInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
        }
      }
    ]
  }
}

// =============================================================================
// Virtual Network
// =============================================================================

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    subnets: [
      {
        name: subnets.functions.name
        properties: {
          addressPrefix: subnets.functions.addressPrefix
          networkSecurityGroup: {
            id: functionsNsg.id
          }
          delegations: [
            {
              name: 'Microsoft.Web.serverFarms'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
          serviceEndpoints: [
            { service: 'Microsoft.Storage' }
            { service: 'Microsoft.KeyVault' }
            { service: 'Microsoft.CognitiveServices' }
          ]
        }
      }
      {
        name: subnets.privateEndpoints.name
        properties: {
          addressPrefix: subnets.privateEndpoints.addressPrefix
          networkSecurityGroup: {
            id: privateEndpointsNsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: subnets.integration.name
        properties: {
          addressPrefix: subnets.integration.addressPrefix
          delegations: [
            {
              name: 'Microsoft.Web.serverFarms'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
    ]
  }
}

// =============================================================================
// Private DNS Zones
// =============================================================================

var privateDnsZones = [
  'privatelink.openai.azure.com'
  'privatelink.search.windows.net'
  'privatelink.documents.azure.com'
  'privatelink.blob.${az.environment().suffixes.storage}'
  'privatelink.vaultcore.azure.net'
]

resource dnsZones 'Microsoft.Network/privateDnsZones@2020-06-01' = [for zone in privateDnsZones: {
  name: zone
  location: 'global'
  tags: tags
}]

resource dnsZoneLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [for (zone, i) in privateDnsZones: {
  parent: dnsZones[i]
  name: '${vnetName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}]

// =============================================================================
// Outputs
// =============================================================================

output vnetId string = vnet.id
output vnetName string = vnet.name
output functionsSubnetId string = '${vnet.id}/subnets/${subnets.functions.name}'
output privateEndpointSubnetId string = '${vnet.id}/subnets/${subnets.privateEndpoints.name}'
output integrationSubnetId string = '${vnet.id}/subnets/${subnets.integration.name}'

output privateDnsZoneIds object = {
  openai: dnsZones[0].id
  search: dnsZones[1].id
  cosmos: dnsZones[2].id
  blob: dnsZones[3].id
  keyVault: dnsZones[4].id
}
