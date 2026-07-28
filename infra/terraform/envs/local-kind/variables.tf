variable "cluster_name" {
  description = "kind cluster name"
  type        = string
  default     = "f1-platform"
}

variable "pipeline_namespace" {
  description = "Namespace for Kafka and the pipeline services"
  type        = string
  default     = "pipeline"
}

variable "kafka_chart_version" {
  description = "Bitnami Kafka chart version (pinned deliberately, see infra/helm/kafka-values.yaml)"
  type        = string
  default     = "32.4.3"
}

variable "faust_processor_image_tag" {
  description = "Image tag for apps/faust-processor (built + kind-loaded locally as telemetry-generator:local / faust-processor:local)"
  type        = string
  default     = "local"
}
