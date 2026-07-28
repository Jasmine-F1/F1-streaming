resource "kubernetes_namespace" "pipeline" {
  metadata {
    name = var.pipeline_namespace
  }

  depends_on = [module.eks]
}

resource "helm_release" "kafka" {
  name       = "kafka"
  repository = "https://charts.bitnami.com/bitnami"
  chart      = "kafka"
  version    = var.kafka_chart_version
  namespace  = kubernetes_namespace.pipeline.metadata[0].name

  # Same values as local dev (infra/helm/kafka-values.yaml: single broker,
  # PLAINTEXT, tiny storage). Fine for a short supervised verification run;
  # a longer-lived deployment would want its own EKS-tuned values (real
  # replication factor, EBS storage class, SASL auth) instead of reusing this.
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

# telemetry-generator: same reasoning as the local-kind env — a run-to-
# completion Job doesn't fit Terraform's continuous reconciliation model,
# triggered manually instead:
#   helm install --generate-name infra/helm/telemetry-generator \
#     -n pipeline --set args.injectFaults=true
