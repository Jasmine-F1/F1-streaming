terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }

  # No remote backend configured — this environment is only ever applied for
  # a short, supervised verification run and torn down immediately after
  # (see CLAUDE.md: any real-money operation needs sign-off first). If this
  # ever becomes a longer-lived environment, add an S3 + DynamoDB backend
  # here before the next apply.
}

provider "aws" {
  region = var.aws_region
}
