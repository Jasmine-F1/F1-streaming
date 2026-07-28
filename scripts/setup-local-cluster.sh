#!/usr/bin/env bash
# Stand up the local kind cluster + Kafka for development.
# Idempotent-ish: safe to re-run (kind/helm no-op if already present).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! kind get clusters 2>/dev/null | grep -qx f1-platform; then
  kind create cluster --config "$REPO_ROOT/infra/kind/kind-config.yaml"
else
  echo "kind cluster 'f1-platform' already exists, skipping create"
fi

kubectl create namespace pipeline --dry-run=client -o yaml | kubectl apply -f -

helm repo add bitnami https://charts.bitnami.com/bitnami >/dev/null 2>&1 || true
helm repo update >/dev/null

helm upgrade --install kafka bitnami/kafka --version 32.4.3 \
  --namespace pipeline \
  -f "$REPO_ROOT/infra/helm/kafka-values.yaml" \
  --wait --timeout 5m

echo "Done. Kafka is reachable in-cluster at kafka.pipeline.svc.cluster.local:9092"
