# Networking Module Outputs

output "vnet_id" {
  description = "ID of the Virtual Network"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Name of the Virtual Network"
  value       = azurerm_virtual_network.main.name
}

output "functions_subnet_id" {
  description = "ID of the Functions subnet"
  value       = azurerm_subnet.functions.id
}

output "vm_subnet_id" {
  description = "ID of the VM subnet"
  value       = azurerm_subnet.vm.id
}

output "private_endpoints_subnet_id" {
  description = "ID of the Private Endpoints subnet"
  value       = azurerm_subnet.private_endpoints.id
}

output "bastion_subnet_id" {
  description = "ID of the Bastion subnet"
  value       = azurerm_subnet.bastion.id
}

output "private_dns_zone_ids" {
  description = "Map of Private DNS Zone IDs"
  value = {
    blob               = azurerm_private_dns_zone.blob.id
    cosmos             = azurerm_private_dns_zone.cosmos.id
    keyvault           = azurerm_private_dns_zone.keyvault.id
    openai             = azurerm_private_dns_zone.openai.id
    search             = azurerm_private_dns_zone.search.id
    cognitiveservices  = azurerm_private_dns_zone.cognitiveservices.id
  }
}

output "bastion_public_ip" {
  description = "Public IP of the Bastion Host"
  value       = azurerm_public_ip.bastion.ip_address
}
