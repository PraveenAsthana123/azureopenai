#===============================================================================
# Enterprise AI Platform - Network Configuration
# Zero-Trust Architecture - VNet, Subnets, NSGs, Private DNS
#===============================================================================

#-------------------------------------------------------------------------------
# Virtual Network
#-------------------------------------------------------------------------------
resource "azurerm_virtual_network" "vnet" {
  name                = "${local.name_prefix}-vnet"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = var.address_space
  tags                = local.common_tags
}

#-------------------------------------------------------------------------------
# Subnets
#-------------------------------------------------------------------------------
resource "azurerm_subnet" "subnets" {
  for_each = var.subnets

  name                 = "${local.name_prefix}-snet-${each.key}"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = [each.value]

  # Enable service endpoints for data services
  service_endpoints = each.key == "data" ? [
    "Microsoft.Storage",
    "Microsoft.Sql",
    "Microsoft.AzureCosmosDB",
    "Microsoft.KeyVault"
  ] : each.key == "compute" ? [
    "Microsoft.ContainerRegistry",
    "Microsoft.Storage"
  ] : each.key == "app" ? [
    "Microsoft.Storage",
    "Microsoft.KeyVault",
    "Microsoft.CognitiveServices"
  ] : []

  # Delegate compute subnet to AKS
  dynamic "delegation" {
    for_each = each.key == "app" ? [1] : []
    content {
      name = "delegation-functions"
      service_delegation {
        name = "Microsoft.Web/serverFarms"
        actions = [
          "Microsoft.Network/virtualNetworks/subnets/action"
        ]
      }
    }
  }
}

#-------------------------------------------------------------------------------
# Network Security Groups
#-------------------------------------------------------------------------------
resource "azurerm_network_security_group" "nsg_app" {
  name                = "${local.name_prefix}-nsg-app"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags

  # Allow HTTPS inbound from APIM
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "ApiManagement"
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_security_group" "nsg_ai" {
  name                = "${local.name_prefix}-nsg-ai"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags

  # Allow internal VNet traffic only
  security_rule {
    name                       = "AllowVNetInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_security_group" "nsg_data" {
  name                = "${local.name_prefix}-nsg-data"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags

  # Allow internal VNet traffic only
  security_rule {
    name                       = "AllowVNetInbound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_security_group" "nsg_compute" {
  name                = "${local.name_prefix}-nsg-compute"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags

  # Allow AKS management traffic
  security_rule {
    name                       = "AllowAKSManagement"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "AzureCloud"
    destination_address_prefix = "*"
  }

  # Allow internal VNet traffic
  security_rule {
    name                       = "AllowVNetInbound"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

#-------------------------------------------------------------------------------
# NSG Subnet Associations
#-------------------------------------------------------------------------------
resource "azurerm_subnet_network_security_group_association" "nsg_app" {
  subnet_id                 = azurerm_subnet.subnets["app"].id
  network_security_group_id = azurerm_network_security_group.nsg_app.id
}

resource "azurerm_subnet_network_security_group_association" "nsg_ai" {
  subnet_id                 = azurerm_subnet.subnets["ai"].id
  network_security_group_id = azurerm_network_security_group.nsg_ai.id
}

resource "azurerm_subnet_network_security_group_association" "nsg_search" {
  subnet_id                 = azurerm_subnet.subnets["search"].id
  network_security_group_id = azurerm_network_security_group.nsg_ai.id
}

resource "azurerm_subnet_network_security_group_association" "nsg_data" {
  subnet_id                 = azurerm_subnet.subnets["data"].id
  network_security_group_id = azurerm_network_security_group.nsg_data.id
}

resource "azurerm_subnet_network_security_group_association" "nsg_compute" {
  subnet_id                 = azurerm_subnet.subnets["compute"].id
  network_security_group_id = azurerm_network_security_group.nsg_compute.id
}

#-------------------------------------------------------------------------------
# Private DNS Zones
#-------------------------------------------------------------------------------
resource "azurerm_private_dns_zone" "zones" {
  for_each = local.private_dns_zones

  name                = each.value
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.common_tags
}

#-------------------------------------------------------------------------------
# Private DNS Zone VNet Links
#-------------------------------------------------------------------------------
resource "azurerm_private_dns_zone_virtual_network_link" "links" {
  for_each = local.private_dns_zones

  name                  = "${local.name_prefix}-dnslink-${each.key}"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.zones[each.key].name
  virtual_network_id    = azurerm_virtual_network.vnet.id
  registration_enabled  = false
  tags                  = local.common_tags
}

#-------------------------------------------------------------------------------
# Route Tables (for Zero-Trust traffic inspection)
#-------------------------------------------------------------------------------
resource "azurerm_route_table" "rt_default" {
  name                          = "${local.name_prefix}-rt-default"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.rg.name
  bgp_route_propagation_enabled = false
  tags                          = local.common_tags

  # Route all traffic through Azure (can be changed to firewall)
  route {
    name                   = "default-route"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "Internet"
  }

  # Keep Azure services direct
  route {
    name                   = "azure-services"
    address_prefix         = "AzureCloud"
    next_hop_type          = "Internet"
  }
}

#-------------------------------------------------------------------------------
# Route Table Associations
#-------------------------------------------------------------------------------
resource "azurerm_subnet_route_table_association" "rt_app" {
  subnet_id      = azurerm_subnet.subnets["app"].id
  route_table_id = azurerm_route_table.rt_default.id
}

resource "azurerm_subnet_route_table_association" "rt_compute" {
  subnet_id      = azurerm_subnet.subnets["compute"].id
  route_table_id = azurerm_route_table.rt_default.id
}
