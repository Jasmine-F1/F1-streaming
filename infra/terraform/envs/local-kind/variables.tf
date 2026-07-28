variable "cluster_name" {
  description = "kind cluster name"
  type        = string
  default     = "f1-platform"
}

variable "pipeline_namespace" {
  description = "Namespace ArgoCD deploys Kafka and the pipeline services into"
  type        = string
  default     = "pipeline"
}

variable "argocd_chart_version" {
  description = "argo-cd Helm chart version"
  type        = string
  default     = "7.7.11"
}
