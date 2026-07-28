resource "kubernetes_namespace" "pipeline" {
  metadata {
    name = var.pipeline_namespace
  }

  depends_on = [kind_cluster.this]
}

resource "helm_release" "kafka" {
  name       = "kafka"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "kafka"
  version    = var.kafka_chart_version
  namespace  = kubernetes_namespace.pipeline.metadata[0].name

  values = [
    file("${path.module}/../../../helm/kafka-values.yaml")
  ]

  wait    = true
  timeout = 300
}

resource "helm_release" "faust_processor" {
  name      = "faust-processor"
  chart     = "${path.module}/../../../helm/faust-processor"
  namespace = kubernetes_namespace.pipeline.metadata[0].name

  set = [
    {
      name  = "image.tag"
      value = var.faust_processor_image_tag
    }
  ]

  wait       = true
  timeout    = 120
  depends_on = [helm_release.kafka]
}

# telemetry-generator is deliberately NOT a managed resource here: it's a
# Kubernetes Job (run-to-completion), not a long-running service, and doesn't
# fit Terraform's continuously-reconciled desired-state model well — applying
# the same Job spec repeatedly wouldn't trigger a new run. It stays a
# manually-triggered chart instead:
#   helm install --generate-name infra/helm/telemetry-generator \
#     -n pipeline --set args.injectFaults=true
