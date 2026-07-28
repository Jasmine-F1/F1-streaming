variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "cluster_name" {
  type    = string
  default = "f1-platform"
}

variable "cluster_version" {
  type    = string
  default = "1.31"
}

variable "node_instance_types" {
  type    = list(string)
  default = ["t3.medium"]
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "pipeline_namespace" {
  type    = string
  default = "pipeline"
}

variable "kafka_chart_version" {
  type    = string
  default = "32.4.3"
}

variable "faust_processor_image_tag" {
  description = "Set to the CI-built/pushed image tag (see .github/workflows) when actually applying this env"
  type        = string
  default     = "local"
}
