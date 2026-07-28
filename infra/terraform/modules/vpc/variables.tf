variable "name" {
  type = string
}

variable "cluster_name" {
  description = "Used only for the kubernetes.io/cluster/<name> subnet tags EKS needs for auto-discovery"
  type        = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "azs" {
  description = "Full AZ names (e.g. us-east-1a), not suffixes — pass the result of a data \"aws_availability_zones\" lookup from the calling env"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.0.101.0/24", "10.0.102.0/24"]
}

variable "tags" {
  type    = map(string)
  default = {}
}
