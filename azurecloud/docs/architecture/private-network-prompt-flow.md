# Private Network Prompt Flow Deployment Topology

## Overview

This document describes the private-network deployment topology for Azure AI Foundry Prompt Flow with the Enterprise RAG Platform. All traffic between components stays within private networks using Azure Private Endpoints.

## Architecture Diagram

```
                           ┌──────────────────────────────────────────────────────────────┐
                           │                      INTERNET                                 │
                           └──────────────────────────┬───────────────────────────────────┘
                                                      │
                                         ┌────────────▼────────────┐
                                         │   Azure Front Door      │
                                         │   (WAF + DDoS)          │
                                         └────────────┬────────────┘
                                                      │ Private Link Service
                           ┌──────────────────────────▼───────────────────────────────────┐
                           │                    VNET: rag-prod-vnet (10.0.0.0/16)         │
                           │                                                               │
    ┌──────────────────────┼───────────────────────────────────────────────────────────────┤
    │                      │                                                               │
    │  ┌───────────────────▼──────────────────┐    ┌─────────────────────────────────┐   │
    │  │   Subnet: snet-app (10.0.1.0/24)      │    │  Subnet: snet-pe (10.0.2.0/24)  │   │
    │  │                                        │    │                                 │   │
    │  │  ┌────────────────────────────────┐   │    │  Private Endpoints:             │   │
    │  │  │  Azure Functions (Premium)      │   │    │  ┌─────────────────────────┐   │   │
    │  │  │  - RAG API                      │───┼────┼─▶│ PE: Azure OpenAI        │   │   │
    │  │  │  - VNet Integration             │   │    │  │ 10.0.2.10               │   │   │
    │  │  │  - Managed Identity             │   │    │  └─────────────────────────┘   │   │
    │  │  └────────────────────────────────┘   │    │  ┌─────────────────────────┐   │   │
    │  │                                        │    │  │ PE: Azure AI Search     │   │   │
    │  │  ┌────────────────────────────────┐   │────┼─▶│ 10.0.2.11               │   │   │
    │  │  │  Prompt Flow Runtime            │   │    │  └─────────────────────────┘   │   │
    │  │  │  (Foundry Managed Compute)      │   │    │  ┌─────────────────────────┐   │   │
    │  │  │  - VNet Injection               │───┼────┼─▶│ PE: Cosmos DB           │   │   │
    │  │  └────────────────────────────────┘   │    │  │ 10.0.2.12               │   │   │
    │  │                                        │    │  └─────────────────────────┘   │   │
    │  └────────────────────────────────────────┘    │  ┌─────────────────────────┐   │   │
    │                                                │  │ PE: Storage Account     │   │   │
    │  ┌────────────────────────────────────────┐   │  │ 10.0.2.13               │   │   │
    │  │  Subnet: snet-foundry (10.0.3.0/24)    │   │  └─────────────────────────┘   │   │
    │  │                                         │   │  ┌─────────────────────────┐   │   │
    │  │  ┌─────────────────────────────────┐   │   │  │ PE: Key Vault           │   │   │
    │  │  │  AI Foundry Hub                  │   │   │  │ 10.0.2.14               │   │   │
    │  │  │  - Managed VNet Isolation        │───┼───┼─▶└─────────────────────────┘   │   │
    │  │  │  - Managed Private Endpoints     │   │   │  ┌─────────────────────────┐   │   │
    │  │  │  - Project Workspace             │   │   │  │ PE: Document Intel      │   │   │
    │  │  └─────────────────────────────────┘   │   │  │ 10.0.2.15               │   │   │
    │  │                                         │   │  └─────────────────────────┘   │   │
    │  └─────────────────────────────────────────┘   │  ┌─────────────────────────┐   │   │
    │                                                │  │ PE: Foundry Project     │   │   │
    │  ┌────────────────────────────────────────┐   │  │ 10.0.2.16               │   │   │
    │  │  Subnet: AzureFirewallSubnet           │   │  └─────────────────────────┘   │   │
    │  │  (10.0.255.0/26)                       │   │                                 │   │
    │  │  ┌─────────────────────────────────┐   │   └─────────────────────────────────┘   │
    │  │  │  Azure Firewall                  │   │                                        │
    │  │  │  - Forced Tunneling              │   │                                        │
    │  │  │  - Egress Control                │   │                                        │
    │  │  └─────────────────────────────────┘   │                                        │
    │  └────────────────────────────────────────┘                                        │
    │                                                                                     │
    └─────────────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────────────────────────┐
    │                           Private DNS Zones (linked to VNet)                         │
    │                                                                                      │
    │  privatelink.openai.azure.com          → Azure OpenAI                               │
    │  privatelink.search.windows.net        → Azure AI Search                            │
    │  privatelink.documents.azure.com       → Cosmos DB                                  │
    │  privatelink.blob.core.windows.net     → Storage Account                            │
    │  privatelink.vaultcore.azure.net       → Key Vault                                  │
    │  privatelink.cognitiveservices.azure.com → Document Intelligence                    │
    │  privatelink.api.azureml.ms            → AI Foundry                                 │
    │  privatelink.notebooks.azure.net       → AI Foundry Notebooks                       │
    │                                                                                      │
    └─────────────────────────────────────────────────────────────────────────────────────┘
```

## Network Isolation Modes

### Mode A: Project Private Link (Recommended for Most Cases)

Create a private endpoint for the Foundry Project for private control plane access.

```hcl
# Terraform: Foundry Project Private Endpoint
resource "azurerm_private_endpoint" "foundry_project" {
  name                = "pe-foundry-project"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = azurerm_subnet.pe.id

  private_service_connection {
    name                           = "foundry-project-connection"
    private_connection_resource_id = azurerm_machine_learning_workspace.foundry.id
    subresource_names              = ["amlworkspace"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "foundry-dns"
    private_dns_zone_ids = [
      azurerm_private_dns_zone.aml_api.id,
      azurerm_private_dns_zone.aml_notebooks.id
    ]
  }
}
```

### Mode B: Hub Managed VNet Isolation (Maximum Security)

Foundry Hub creates a Microsoft-managed VNet with outbound isolation.

```bicep
// Bicep: AI Foundry Hub with Managed Network Isolation
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-01-01-preview' = {
  name: hubName
  location: location
  kind: 'Hub'
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: 'RAG Platform Hub'
    publicNetworkAccess: 'Disabled'
    managedNetwork: {
      isolationMode: 'AllowOnlyApprovedOutbound'
      outboundRules: {
        // Allow outbound to your private endpoints
        'openai-pe': {
          type: 'PrivateEndpoint'
          destination: {
            serviceResourceId: openaiAccount.id
            subresourceTarget: 'account'
          }
        }
        'search-pe': {
          type: 'PrivateEndpoint'
          destination: {
            serviceResourceId: searchService.id
            subresourceTarget: 'searchService'
          }
        }
        'cosmos-pe': {
          type: 'PrivateEndpoint'
          destination: {
            serviceResourceId: cosmosAccount.id
            subresourceTarget: 'sql'
          }
        }
      }
    }
  }
}
```

## Private Endpoints Checklist

| Service | Private Endpoint | Private DNS Zone | Required |
|---------|------------------|------------------|----------|
| Azure OpenAI | `account` | `privatelink.openai.azure.com` | Yes |
| Azure AI Search | `searchService` | `privatelink.search.windows.net` | Yes |
| Cosmos DB | `sql` | `privatelink.documents.azure.com` | Yes |
| Storage (Blob) | `blob` | `privatelink.blob.core.windows.net` | Yes |
| Key Vault | `vault` | `privatelink.vaultcore.azure.net` | Yes |
| Document Intelligence | `account` | `privatelink.cognitiveservices.azure.com` | Yes |
| AI Foundry Project | `amlworkspace` | `privatelink.api.azureml.ms` | Optional |
| AI Foundry Hub | `amlworkspace` | `privatelink.api.azureml.ms` | Optional |

## Bicep Implementation

### Private Endpoints Module

```bicep
// modules/private-endpoints.bicep

param location string
param vnetId string
param peSubnetId string
param openaiId string
param searchId string
param cosmosId string
param storageId string
param kvId string
param docintelId string

// Private DNS Zones
var privateDnsZones = [
  { name: 'privatelink.openai.azure.com', resourceId: openaiId, groupId: 'account' }
  { name: 'privatelink.search.windows.net', resourceId: searchId, groupId: 'searchService' }
  { name: 'privatelink.documents.azure.com', resourceId: cosmosId, groupId: 'sql' }
  { name: 'privatelink.blob.core.windows.net', resourceId: storageId, groupId: 'blob' }
  { name: 'privatelink.vaultcore.azure.net', resourceId: kvId, groupId: 'vault' }
  { name: 'privatelink.cognitiveservices.azure.com', resourceId: docintelId, groupId: 'account' }
]

// Create DNS Zones
resource dnsZones 'Microsoft.Network/privateDnsZones@2020-06-01' = [for zone in privateDnsZones: {
  name: zone.name
  location: 'global'
}]

// Link DNS Zones to VNet
resource dnsVnetLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = [for (zone, i) in privateDnsZones: {
  parent: dnsZones[i]
  name: 'link-${uniqueString(vnetId)}'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnetId }
    registrationEnabled: false
  }
}]

// Create Private Endpoints
resource privateEndpoints 'Microsoft.Network/privateEndpoints@2023-05-01' = [for (zone, i) in privateDnsZones: {
  name: 'pe-${replace(zone.name, 'privatelink.', '')}'
  location: location
  properties: {
    subnet: { id: peSubnetId }
    privateLinkServiceConnections: [
      {
        name: 'plsc-${zone.groupId}'
        properties: {
          privateLinkServiceId: zone.resourceId
          groupIds: [zone.groupId]
        }
      }
    ]
  }
}]

// DNS Zone Groups for automatic DNS registration
resource dnsZoneGroups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = [for (zone, i) in privateDnsZones: {
  parent: privateEndpoints[i]
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: zone.name
        properties: {
          privateDnsZoneId: dnsZones[i].id
        }
      }
    ]
  }
}]
```

## Network Security Groups (NSG)

### Application Subnet NSG

```bicep
resource nsgApp 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: 'nsg-app-subnet'
  location: location
  properties: {
    securityRules: [
      {
        name: 'AllowHTTPS'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourceAddressPrefix: 'AzureFrontDoor.Backend'
          sourcePortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '443'
        }
      }
      {
        name: 'DenyAllInbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '*'
        }
      }
    ]
  }
}
```

## Azure Firewall Rules

### Application Rules for Foundry

```bicep
resource fwAppRules 'Microsoft.Network/azureFirewalls/applicationRuleCollections@2023-05-01' = {
  parent: firewall
  name: 'foundry-rules'
  properties: {
    priority: 100
    action: { type: 'Allow' }
    rules: [
      {
        name: 'AzureML-Dependencies'
        sourceAddresses: ['10.0.1.0/24', '10.0.3.0/24']
        targetFqdns: [
          '*.blob.core.windows.net'
          '*.queue.core.windows.net'
          '*.table.core.windows.net'
          'ml.azure.com'
          '*.ml.azure.com'
          'aznbcontent.net'
          '*.aznbcontent.net'
        ]
        protocols: [{ protocolType: 'Https', port: 443 }]
      }
      {
        name: 'Python-Packages'
        sourceAddresses: ['10.0.3.0/24']
        targetFqdns: [
          'pypi.org'
          'files.pythonhosted.org'
          'anaconda.com'
          '*.anaconda.com'
        ]
        protocols: [{ protocolType: 'Https', port: 443 }]
      }
    ]
  }
}
```

## Traffic Flow

### Prompt Flow Runtime → RAG Services

1. **User Request** → Front Door (WAF) → Private Link Service
2. **Function App** receives request in `snet-app`
3. **Prompt Flow** (if invoked) runs in `snet-foundry` managed compute
4. Both call services via **Private Endpoints** in `snet-pe`:
   - Azure OpenAI: `10.0.2.10`
   - Azure AI Search: `10.0.2.11`
   - Cosmos DB: `10.0.2.12`
5. All DNS resolution through **Private DNS Zones**
6. No traffic exits to public internet

## Deployment Steps

### Step 1: Create VNet and Subnets

```bash
az network vnet create \
  --name rag-prod-vnet \
  --resource-group rg-rag-prod \
  --address-prefix 10.0.0.0/16

az network vnet subnet create \
  --vnet-name rag-prod-vnet \
  --name snet-app \
  --address-prefixes 10.0.1.0/24

az network vnet subnet create \
  --vnet-name rag-prod-vnet \
  --name snet-pe \
  --address-prefixes 10.0.2.0/24 \
  --disable-private-endpoint-network-policies true

az network vnet subnet create \
  --vnet-name rag-prod-vnet \
  --name snet-foundry \
  --address-prefixes 10.0.3.0/24
```

### Step 2: Create Private DNS Zones

```bash
zones=(
  "privatelink.openai.azure.com"
  "privatelink.search.windows.net"
  "privatelink.documents.azure.com"
  "privatelink.blob.core.windows.net"
  "privatelink.vaultcore.azure.net"
  "privatelink.cognitiveservices.azure.com"
)

for zone in "${zones[@]}"; do
  az network private-dns zone create \
    --resource-group rg-rag-prod \
    --name "$zone"

  az network private-dns link vnet create \
    --resource-group rg-rag-prod \
    --zone-name "$zone" \
    --name "link-rag-vnet" \
    --virtual-network rag-prod-vnet \
    --registration-enabled false
done
```

### Step 3: Create Private Endpoints

```bash
# Example: Azure OpenAI
az network private-endpoint create \
  --name pe-openai \
  --resource-group rg-rag-prod \
  --vnet-name rag-prod-vnet \
  --subnet snet-pe \
  --private-connection-resource-id /subscriptions/.../openai-account \
  --group-id account \
  --connection-name openai-connection
```

### Step 4: Disable Public Access

```bash
# Disable public access on all services
az cognitiveservices account update \
  --name rag-aoai-prod \
  --resource-group rg-rag-prod \
  --public-network-access Disabled

az search service update \
  --name rag-search-prod \
  --resource-group rg-rag-prod \
  --public-network-access Disabled
```

### Step 5: Configure AI Foundry Managed Network

```bash
az ml workspace update \
  --name foundry-hub \
  --resource-group rg-rag-prod \
  --managed-network isolation-mode allow-only-approved-outbound
```

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| DNS resolution fails | Missing DNS zone link | Link private DNS zone to VNet |
| Connection timeout | NSG blocking traffic | Add NSG rule for PE subnet |
| "Forbidden" from OpenAI | Public access disabled, no PE | Create private endpoint |
| Foundry can't reach services | Missing outbound rules | Add managed PE in Hub config |
| Functions timeout | VNet integration misconfigured | Enable VNet integration on Premium plan |

## Validation Checklist

- [ ] All private endpoints show "Succeeded" status
- [ ] DNS zones linked to VNet
- [ ] A-records auto-created for each PE
- [ ] `nslookup` resolves to private IPs from within VNet
- [ ] Public access disabled on all services
- [ ] Functions can reach services via PE
- [ ] Prompt Flow runtime can access resources
- [ ] No egress to public internet (verify with Firewall logs)
