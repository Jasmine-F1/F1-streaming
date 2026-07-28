module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = var.vpc_id
  subnet_ids = var.private_subnet_ids

  enable_irsa = true

  cluster_endpoint_public_access = true # this cluster only exists for a short,
  # supervised verification run — not worth setting up bastion/VPN access for it

  eks_managed_node_groups = {
    default = {
      instance_types = var.node_instance_types
      capacity_type  = "SPOT" # cost-conscious — same reasoning as single_nat_gateway
      min_size       = 1
      max_size       = 2
      desired_size   = var.node_desired_size
    }
  }

  tags = var.tags
}
