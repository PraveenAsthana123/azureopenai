# Cache Module - Redis Cache for Query, Retrieval, and Embedding Caching
# Implements caching strategy as per LLD

resource "azurerm_redis_cache" "main" {
  name                = "redis-${var.project_name}-${var.environment}-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  capacity            = var.environment == "prod" ? 2 : 1
  family              = var.environment == "prod" ? "P" : "C"
  sku_name            = var.environment == "prod" ? "Premium" : "Standard"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"

  # Premium features for production
  dynamic "redis_configuration" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      maxmemory_reserved              = 50
      maxmemory_delta                 = 50
      maxmemory_policy                = "allkeys-lru"
      maxfragmentationmemory_reserved = 50
    }
  }

  # VNet integration for Premium
  dynamic "patch_schedule" {
    for_each = var.environment == "prod" ? [1] : []
    content {
      day_of_week    = "Sunday"
      start_hour_utc = 2
    }
  }

  public_network_access_enabled = false

  tags = var.tags
}

# Private Endpoint
resource "azurerm_private_endpoint" "redis" {
  name                = "pe-redis-${var.resource_suffix}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.subnet_id
  tags                = var.tags

  private_service_connection {
    name                           = "psc-redis"
    private_connection_resource_id = azurerm_redis_cache.main.id
    is_manual_connection           = false
    subresource_names              = ["redisCache"]
  }

  private_dns_zone_group {
    name                 = "dns-zone-group"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
}

# Output connection info
output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "redis_ssl_port" {
  value = azurerm_redis_cache.main.ssl_port
}

output "redis_primary_access_key" {
  value     = azurerm_redis_cache.main.primary_access_key
  sensitive = true
}

output "redis_primary_connection_string" {
  value     = azurerm_redis_cache.main.primary_connection_string
  sensitive = true
}
