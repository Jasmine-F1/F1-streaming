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

variable "argocd_chart_version" {
  type    = string
  default = "7.7.11"
}
