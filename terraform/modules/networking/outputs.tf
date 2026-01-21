# =============================================================================
# Networking Module - Outputs
# =============================================================================

output "vnet_id" {
  description = "Virtual network ID"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Virtual network name"
  value       = azurerm_virtual_network.main.name
}

output "subnet_ids" {
  description = "Map of subnet names to IDs"
  value       = { for k, v in azurerm_subnet.subnets : k => v.id }
}

output "private_dns_zone_ids" {
  description = "Map of private DNS zone names to IDs"
  value       = { for k, v in azurerm_private_dns_zone.zones : k => v.id }
}

output "private_dns_zone_names" {
  description = "Map of private DNS zone keys to zone names"
  value       = { for k, v in azurerm_private_dns_zone.zones : k => v.name }
}
