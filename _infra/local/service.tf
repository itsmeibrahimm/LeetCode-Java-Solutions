provider "archive" {
  version = "1.2.2"
}

provider "kubernetes" {
  version = "1.8.1"
}

provider "helm" {
  kubernetes {
    config_context = "docker-for-desktop"
  }
  install_tiller = false
  version = "0.10.1" # Heredoc strings delimited by commas broken in 0.10.2
}

module "payment-service-web" {
  source = "git::https://github.com/doordash/terraform-kubernetes-microservice.git?ref=master"

  namespace                                 = "payment-service"
  service_name                              = "payment-service"
  service_app                               = "web"
  service_contact_info                      = "eng-payment@doordash.com"
  service_docker_image                      = "payment-service"
  service_docker_image_tag                  = "localbuild"
  service_image_pull_policy                 = "Never"

  service_max_surge                         = "100%"
  service_max_unavailable                   = "0"
  service_replica_count                     = "1"
  service_container_port                    = "80"

  service_resource_requests_memory          = "1Gi"
  service_resource_limits_memory            = "1Gi"
  service_resource_requests_cpu             = "1024m"
  service_resource_limits_cpu               = "1024m"

  service_readiness_probe_path              = "/health"
  service_readiness_probe_init_delay        = 30
  service_readiness_probe_period            = 5
  service_readiness_probe_failure_threshold = 3

  runtime_enable                            = "false"

  net_service_enable                        = "true"
  net_service_type                          = "ClusterIP"
  net_service_port                          = "80"

  service_environments_variables = <<EOF
    ENVIRONMENT=local
   EOF
}

module "payment-service-cron" {
  source = "git::https://github.com/doordash/terraform-kubernetes-microservice.git?ref=master"

  namespace                                 = "payment-service"
  service_name                              = "payment-service"
  service_app                               = "cron"
  service_contact_info                      = "eng-payment@doordash.com"
  service_docker_image                      = "payment-service"
  service_docker_image_tag                  = "localbuild"
  service_image_pull_policy                 = "Never"

  service_cmd                               = "python"
  service_cmd_args                          = "app/payin_cron.py"

  service_max_surge                         = "100%"
  service_max_unavailable                   = "0"
  service_replica_count                     = "1"
  service_container_port                    = "80"

  service_resource_requests_memory          = "2Gi"
  service_resource_limits_memory            = "2Gi"
  service_resource_requests_cpu             = "1024m"
  service_resource_limits_cpu               = "1024m"

  service_liveness_probe_init_delay         = "20"
  service_liveness_probe_period             = "10"
  service_liveness_probe_failure_threshold  = "3"
  service_liveness_probe_path               = "/"

  runtime_enable                            = "false"

  net_service_enable                        = "true"
  net_service_type                          = "ClusterIP"
  net_service_port                          = "80"

  service_environments_variables = <<EOF
    ENVIRONMENT=local
   EOF
}

module "payment-service-payout-cron" {
  source = "git::https://github.com/doordash/terraform-kubernetes-microservice.git?ref=master"

  namespace                                 = "payment-service"
  service_name                              = "payment-service"
  service_app                               = "payout-cron"
  service_contact_info                      = "eng-payment@doordash.com"
  service_docker_image                      = "payment-service"
  service_docker_image_tag                  = "localbuild"
  service_image_pull_policy                 = "Never"

  service_cmd                               = "python"
  service_cmd_args                          = "app/payout_cron.py"

  service_max_surge                         = "100%"
  service_max_unavailable                   = "0"
  service_replica_count                     = "1"
  service_container_port                    = "80"

  service_resource_requests_memory          = "2Gi"
  service_resource_limits_memory            = "2Gi"
  service_resource_requests_cpu             = "1024m"
  service_resource_limits_cpu               = "1024m"

  service_liveness_probe_init_delay         = "20"
  service_liveness_probe_period             = "10"
  service_liveness_probe_failure_threshold  = "3"
  service_liveness_probe_path               = "/"

  runtime_enable                            = "false"

  net_service_enable                        = "true"
  net_service_type                          = "ClusterIP"
  net_service_port                          = "80"

  service_environments_variables = <<EOF
    ENVIRONMENT=local
   EOF
}

module "payment-service-delete-payer-cron" {
  source = "git::https://github.com/doordash/terraform-kubernetes-microservice.git?ref=master"

  namespace                                 = "payment-service"
  service_name                              = "payment-service"
  service_app                               = "delete-payer-cron"
  service_contact_info                      = "eng-payment@doordash.com"
  service_docker_image                      = "payment-service"
  service_docker_image_tag                  = "localbuild"
  service_image_pull_policy                 = "Never"

  service_cmd                               = "python"
  service_cmd_args                          = "app/delete_payer_cron.py"

  service_max_surge                         = "100%"
  service_max_unavailable                   = "0"
  service_replica_count                     = "1"
  service_container_port                    = "80"

  service_resource_requests_memory          = "2Gi"
  service_resource_limits_memory            = "2Gi"
  service_resource_requests_cpu             = "1024m"
  service_resource_limits_cpu               = "1024m"

  service_liveness_probe_init_delay         = "20"
  service_liveness_probe_period             = "10"
  service_liveness_probe_failure_threshold  = "3"
  service_liveness_probe_path               = "/"

  runtime_enable                            = "false"

  net_service_enable                        = "true"
  net_service_type                          = "ClusterIP"
  net_service_port                          = "80"

  service_environments_variables = <<EOF
    ENVIRONMENT=local
   EOF
}

module "payment-service-admin" {
  source = "git::ssh://git@github.com/doordash/terraform-kubernetes-microservice.git?ref=master"

  namespace                                 = "payment-service"
  service_name                              = "payment-service"
  service_app                               = "admin"
  service_contact_info                      = "eng-payment@doordash.com"
  service_docker_image                      = "payment-service"
  service_docker_image_tag                  = "localbuild"
  service_image_pull_policy                 = "Never"
  service_cmd                               = "tail"
  service_cmd_args                          = "-f, /dev/null"

  service_max_surge                         = "100%"
  service_max_unavailable                   = "0"
  service_replica_count                     = "1"
  service_container_port                    = "80"

  service_resource_requests_memory          = "1Gi"
  service_resource_limits_memory            = "1Gi"
  service_resource_requests_cpu             = "1024m"
  service_resource_limits_cpu               = "1024m"

  runtime_enable                            = "false"

  net_service_enable                        = "true"
  net_service_port                          = "80"
  net_service_type                          = "ClusterIP"

  service_environments_variables = <<EOF
    ENVIRONMENT=local
   EOF
}
