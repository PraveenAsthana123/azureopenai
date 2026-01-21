#===============================================================================
# MLC LLM Module - Kubernetes Deployments for GPU Inference
#===============================================================================

variable "name_prefix" { type = string }
variable "resource_group_name" { type = string }
variable "location" { type = string }
variable "aks_cluster_name" { type = string }
variable "acr_login_server" { type = string }
variable "storage_account_name" { type = string }
variable "mlc_llm_models" { type = any }
variable "tags" { type = map(string) }

#-------------------------------------------------------------------------------
# Kubernetes Namespace
#-------------------------------------------------------------------------------
resource "kubernetes_namespace" "mlc_llm" {
  metadata {
    name = "mlc-llm"
    labels = {
      "app.kubernetes.io/name"       = "mlc-llm"
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

#-------------------------------------------------------------------------------
# ConfigMap for MLC LLM Configuration
#-------------------------------------------------------------------------------
resource "kubernetes_config_map" "mlc_llm_config" {
  metadata {
    name      = "mlc-llm-config"
    namespace = kubernetes_namespace.mlc_llm.metadata[0].name
  }

  data = {
    "serve-config.yaml" = yamlencode({
      server = {
        host            = "0.0.0.0"
        port            = 8080
        enable_debug    = false
        enable_metrics  = true
        metrics_port    = 9090
      }
      models = [for model in var.mlc_llm_models : {
        name           = model.name
        model_id       = model.model_id
        quantization   = model.quantization
        max_batch_size = model.max_batch_size
        tensor_parallel_shards = model.gpu_count
      }]
      optimization = {
        enable_speculative_decoding = true
        kv_cache_page_size         = 16
        prefill_chunk_size         = 2048
      }
    })
  }
}

#-------------------------------------------------------------------------------
# MLC LLM Deployments
#-------------------------------------------------------------------------------
resource "kubernetes_deployment" "mlc_llm" {
  for_each = { for model in var.mlc_llm_models : model.name => model }

  metadata {
    name      = "mlc-llm-${each.value.name}"
    namespace = kubernetes_namespace.mlc_llm.metadata[0].name
    labels = {
      app   = "mlc-llm"
      model = each.value.name
    }
  }

  spec {
    replicas = each.value.replicas

    selector {
      match_labels = {
        app   = "mlc-llm"
        model = each.value.name
      }
    }

    template {
      metadata {
        labels = {
          app   = "mlc-llm"
          model = each.value.name
        }
        annotations = {
          "prometheus.io/scrape" = "true"
          "prometheus.io/port"   = "9090"
        }
      }

      spec {
        node_selector = {
          "gpu-type" = each.value.gpu_type
        }

        toleration {
          key      = "nvidia.com/gpu"
          operator = "Equal"
          value    = "true"
          effect   = "NoSchedule"
        }

        container {
          name  = "mlc-llm"
          image = "${var.acr_login_server}/mlc-llm:latest"

          port {
            container_port = 8080
            name           = "http"
          }

          port {
            container_port = 9090
            name           = "metrics"
          }

          env {
            name  = "MODEL_NAME"
            value = each.value.name
          }

          env {
            name  = "MODEL_ID"
            value = each.value.model_id
          }

          env {
            name  = "QUANTIZATION"
            value = each.value.quantization
          }

          env {
            name  = "MAX_BATCH_SIZE"
            value = tostring(each.value.max_batch_size)
          }

          env {
            name  = "TENSOR_PARALLEL_SHARDS"
            value = tostring(each.value.gpu_count)
          }

          resources {
            limits = {
              "nvidia.com/gpu" = each.value.gpu_count
              memory           = each.value.gpu_type == "a100" ? "160Gi" : "32Gi"
            }
            requests = {
              "nvidia.com/gpu" = each.value.gpu_count
              memory           = each.value.gpu_type == "a100" ? "160Gi" : "32Gi"
            }
          }

          volume_mount {
            name       = "config"
            mount_path = "/app/config"
          }

          volume_mount {
            name       = "model-cache"
            mount_path = "/models"
          }

          liveness_probe {
            http_get {
              path = "/health"
              port = 8080
            }
            initial_delay_seconds = 300
            period_seconds        = 30
          }

          readiness_probe {
            http_get {
              path = "/ready"
              port = 8080
            }
            initial_delay_seconds = 60
            period_seconds        = 10
          }
        }

        volume {
          name = "config"
          config_map {
            name = kubernetes_config_map.mlc_llm_config.metadata[0].name
          }
        }

        volume {
          name = "model-cache"
          empty_dir {
            size_limit = "200Gi"
          }
        }
      }
    }
  }
}

#-------------------------------------------------------------------------------
# Services
#-------------------------------------------------------------------------------
resource "kubernetes_service" "mlc_llm" {
  for_each = { for model in var.mlc_llm_models : model.name => model }

  metadata {
    name      = "mlc-llm-${each.value.name}"
    namespace = kubernetes_namespace.mlc_llm.metadata[0].name
    labels = {
      app   = "mlc-llm"
      model = each.value.name
    }
  }

  spec {
    selector = {
      app   = "mlc-llm"
      model = each.value.name
    }

    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }

    port {
      name        = "metrics"
      port        = 9090
      target_port = 9090
    }

    type = "ClusterIP"
  }
}

#-------------------------------------------------------------------------------
# MLC LLM Gateway Service
#-------------------------------------------------------------------------------
resource "kubernetes_service" "mlc_llm_gateway" {
  metadata {
    name      = "mlc-llm-gateway"
    namespace = kubernetes_namespace.mlc_llm.metadata[0].name
    labels = {
      app = "mlc-llm-gateway"
    }
  }

  spec {
    selector = {
      app = "mlc-llm-router"
    }

    port {
      name        = "http"
      port        = 80
      target_port = 8080
    }

    type = "LoadBalancer"

    load_balancer_source_ranges = ["10.0.0.0/8"]
  }
}

#-------------------------------------------------------------------------------
# Horizontal Pod Autoscalers
#-------------------------------------------------------------------------------
resource "kubernetes_horizontal_pod_autoscaler_v2" "mlc_llm" {
  for_each = { for model in var.mlc_llm_models : model.name => model }

  metadata {
    name      = "mlc-llm-${each.value.name}-hpa"
    namespace = kubernetes_namespace.mlc_llm.metadata[0].name
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = "mlc-llm-${each.value.name}"
    }

    min_replicas = each.value.replicas
    max_replicas = each.value.replicas * 3

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }
  }
}

#-------------------------------------------------------------------------------
# Outputs
#-------------------------------------------------------------------------------
output "mlc_llm_namespace" {
  value = kubernetes_namespace.mlc_llm.metadata[0].name
}

output "mlc_llm_services" {
  value = { for k, v in kubernetes_service.mlc_llm : k => v.metadata[0].name }
}
