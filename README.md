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
Terraform (VPC / EKS / IAM)
  -> Kubernetes (kind locally, AWS EKS for the final demo)
    -> Helm charts (package each pipeline service)
      -> GitHub Actions CI/CD (build -> test -> push image)
        -> ArgoCD (GitOps sync)
          -> Prometheus / Grafana / Loki (observability)
```

## Repo layout

- `apps/` — pipeline services (telemetry generator, Faust processor, MCP copilot)
- `infra/` — Terraform, Helm charts, kind config, ArgoCD manifests
- `observability/` — Prometheus rules, Grafana dashboards, Loki config
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
- [ ] `apps/mcp-copilot` (Claude MCP server)
- [ ] AWS EKS validation run
