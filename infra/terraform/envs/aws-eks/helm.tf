resource "kubernetes_namespace" "pipeline" {
  metadata {
    name = var.pipeline_namespace
  }

  depends_on = [module.eks]
}

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }

  depends_on = [module.eks]
}

# Same split as the local-kind env: Terraform provisions the cluster and
# bootstraps ArgoCD; everything that runs on the cluster (Kafka,
# faust-processor) is an ArgoCD Application (infra/argocd/apps/) synced from
# git, not a helm_release here.
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = var.argocd_chart_version
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  wait    = true
  timeout = 300
}

# telemetry-generator: same reasoning as the local-kind env — a run-to-
# completion Job doesn't fit continuous GitOps reconciliation, triggered
# manually instead:
#   helm install --generate-name infra/helm/telemetry-generator \
#     -n pipeline --set args.injectFaults=true
