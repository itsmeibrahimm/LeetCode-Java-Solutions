variable "k8s_config_path" {
  type = string
}

variable "image_tag" {
  type = string
}

variable "namespace" {
  type = string
}

variable "service_name" {
  type = string
}

variable "blue_green_first_deployment" {
  type = string
}

provider "aws" {
  region  = "us-west-2"
  version = "2.23.0"
}

provider "kubernetes" {
  config_path = var.k8s_config_path
  version = "1.8.1"
}

provider "helm" {
  kubernetes {
    config_path = var.k8s_config_path
  }
  install_tiller = false
  version = "0.10.1" # Heredoc strings delimited by commas broken in 0.10.2
}
