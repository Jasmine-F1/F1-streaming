# F1 Real-Time Data Platform

A portfolio project for a **Platform Engineer** role (Williams F1 Racing).
The core focus is platform engineering — Kubernetes, Terraform, Helm, CI/CD,
GitOps, and observability. The F1 telemetry pipeline is just the sample
workload running on top of that platform, not the point of the project.

See [CLAUDE.md](CLAUDE.md) for full background, architecture, and decisions.

## Architecture

**Application layer (pipeline):**

```
Telemetry Generator -> Kafka -> Faust stream processing -> validation + feature engineering
                                                    |-> Prometheus Alertmanager (alerts)
                                                    |-> Grafana (mission control dashboard)
                                                    `-> Claude MCP Copilot (natural-language queries)
```

**Platform layer (deploys and operates the application layer):**

```
Terraform                              GitHub Actions CI/CD
  -> kind locally / AWS EKS              build -> test -> push image -> GHCR
  -> installs ArgoCD                              |
        |                                          v
        v                                 ArgoCD pulls the chart + image
   ArgoCD (GitOps sync, reading from this repo)
    -> Kafka (Bitnami chart)
    -> faust-processor (own chart: app + ServiceMonitor + PrometheusRule + Grafana dashboard)
    -> kube-prometheus-stack (Prometheus + Alertmanager + Grafana)
```

Terraform's job stops at "the cluster exists, ArgoCD is installed" — it does
**not** deploy Kafka/faust-processor/observability directly (an earlier
version of this project had it do that via `helm_release`, but that fights
ArgoCD for ownership of the same resources; see
[docs/architecture.md](docs/architecture.md) for why). GitHub Actions is a
separate, parallel pipeline that only builds and publishes images — it
doesn't deploy anything either; ArgoCD is the only thing that changes what's
actually running on the cluster.

## Repo layout

- `apps/` — pipeline services (telemetry generator, Faust processor, MCP copilot)
- `infra/` — Terraform (cluster + ArgoCD only), Helm charts (Kafka values,
  faust-processor's own chart incl. its ServiceMonitor/PrometheusRule/Grafana
  dashboard, kube-prometheus-stack values), kind config, ArgoCD Application
  manifests
- `docs/` — architecture notes and design decisions
- `scripts/` — local dev helper scripts

## Status

See [docs/progress-log.md](docs/progress-log.md) for a step-by-step build
log (what was done, why, and how it was verified). See CLAUDE.md for the
1-2 week build timeline.

- [x] Repo scaffolding
- [x] `apps/telemetry-generator` (FastF1 replay -> Kafka)
- [x] Local `kind` cluster + Kafka (Bitnami Helm chart), verified end-to-end
- [x] `apps/faust-processor` (validation + feature engineering, verified end-to-end)
- [x] Helm charts for both services + Terraform for local-kind (verified: `terraform apply` from a clean slate reproduces the whole pipeline)
- [x] Terraform AWS EKS env scaffolded + `validate`d against real registry modules (not applied — needs sign-off first)
- [x] GitHub Actions CI (build/test/push, path-filtered), verified against real GitHub Actions runs
- [x] ArgoCD GitOps (Terraform provisions cluster + ArgoCD only; ArgoCD deploys Kafka/faust-processor from git), verified end-to-end
- [x] Prometheus/Alertmanager + Grafana (kube-prometheus-stack via ArgoCD), scraping + alert firing verified
- [x] Grafana "mission control" dashboard (12 panels, GitOps-provisioned via ConfigMap sidecar), verified end-to-end through Grafana's own query path
- [ ] `apps/mcp-copilot` (Claude MCP server)
- [ ] AWS EKS validation run
