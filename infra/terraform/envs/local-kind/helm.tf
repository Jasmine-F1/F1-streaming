resource "kubernetes_namespace" "pipeline" {
  metadata {
    name = var.pipeline_namespace
  }

  depends_on = [kind_cluster.this]
}

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }

  depends_on = [kind_cluster.this]
}

# Terraform's job stops at "the cluster exists" (per the architecture: infra
# up through K8s is Terraform's layer, everything deployed *onto* it is
# ArgoCD's GitOps layer — see docs/architecture.md). ArgoCD itself is the one
# exception installed here rather than via GitOps, since it has to exist
# before it can bootstrap anything else. Kafka and faust-processor used to be
# helm_release resources in this file; they're now ArgoCD Applications
# instead (infra/argocd/apps/) so Terraform and ArgoCD aren't both trying to
# own the same resources.
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  # Local kind dev only: serve the API/UI over plain HTTP so `kubectl
  # port-forward` + a browser just works, no cert setup. Never do this on a
  # real cluster.
  set = [
    {
      name  = "configs.params.server\\.insecure"
      value = "true"
    }
  ]

  wait    = true
  timeout = 300
}

# telemetry-generator is deliberately not GitOps-managed either: it's a
# Kubernetes Job (run-to-completion), not a long-running service, and doesn't
# fit continuous reconciliation (ArgoCD would just see "Job already exists,
# nothing to sync" — re-syncing wouldn't trigger a new run). It stays a
# manually-triggered chart:
#   helm install --generate-name infra/helm/telemetry-generator \
#     -n pipeline --set args.injectFaults=true
