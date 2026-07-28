# Local dev cluster. This replaces manually running `kind create cluster` +
# `helm install` by hand (what scripts/setup-local-cluster.sh did) with a
# single `terraform apply`.
#
# NOTE: the tehcyx/kind provider's kind_config takes typed HCL blocks, not a
# raw kind YAML file — it can't just `file()` ../../kind/kind-config.yaml.
# That file still exists as the manual-CLI fallback (`kind create cluster
# --config ...`, no terraform required); keep the node topology below in
# sync with it if either changes (currently: 1 control-plane + 2 workers).
resource "kind_cluster" "this" {
  name           = var.cluster_name
  wait_for_ready = true

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    node {
      role = "control-plane"
    }
    node {
      role = "worker"
    }
    node {
      role = "worker"
    }
  }
}

provider "helm" {
  kubernetes = {
    host                   = kind_cluster.this.endpoint
    client_certificate     = kind_cluster.this.client_certificate
    client_key             = kind_cluster.this.client_key
    cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
  }
}

provider "kubernetes" {
  host                   = kind_cluster.this.endpoint
  client_certificate     = kind_cluster.this.client_certificate
  client_key             = kind_cluster.this.client_key
  cluster_ca_certificate = kind_cluster.this.cluster_ca_certificate
}
