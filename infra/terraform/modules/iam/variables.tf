variable "cluster_name" {
  type = string
}

variable "namespace" {
  type    = string
  default = "pipeline"
}

variable "service_account_name" {
  type    = string
  default = "pipeline"
}

variable "oidc_provider_arn" {
  type = string
}

variable "oidc_provider_url" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
