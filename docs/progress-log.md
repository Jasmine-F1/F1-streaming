# Progress Log

Chronological build log for this project. Newest entry on top. See
[README.md](../README.md) for the current architecture snapshot and
[CLAUDE.md](../CLAUDE.md) for goals/decisions that shouldn't drift.

---

## Week 1, Day 5-7 — Helm charts, Terraform (local + AWS scaffold), GitHub Actions CI

**What**: formalized everything built by hand so far into reproducible,
version-controlled infrastructure.

**Helm charts** (`infra/helm/{telemetry-generator,faust-processor}/`):
- `telemetry-generator`: a `Job` (run-to-completion, `ttlSecondsAfterFinished`
  so finished runs self-clean instead of needing manual `kubectl delete pod`
  like during Week 1 testing), all CLI flags parameterized via `values.yaml`
  including a conditional block for `--inject-faults`/`--fault-rate`.
- `faust-processor`: a `Deployment` + `Service` (port 6066), config via env
  vars per `values.yaml`, matching what the app already reads.
- Both linted clean and template-rendered correctly (including the
  conditional fault-injection args) before ever touching a cluster.

**Terraform, local-kind env** (`infra/terraform/envs/local-kind/`): replaces
manually running `kind create cluster` + `helm install` (what
`scripts/setup-local-cluster.sh` did) with `terraform apply`, using the
`tehcyx/kind` provider for the cluster and `helm_release` resources for
Kafka + faust-processor.
- **`telemetry-generator` is deliberately NOT Terraform-managed** — a
  run-to-completion Job doesn't fit continuous state reconciliation
  (re-applying the same Job spec doesn't trigger a new run). It stays a
  manually-triggered `helm install --generate-name` instead, documented
  inline in `helm.tf`.
- Two real snags, both from the `tehcyx/kind` provider's schema not matching
  assumptions:
  1. `kind_config` takes typed HCL blocks, not a raw YAML file — `file()`-ing
     `infra/kind/kind-config.yaml` failed with "Unsupported argument".
     `infra/kind/kind-config.yaml` still exists as the manual-CLI fallback
     (no terraform required); the HCL block in `main.tf` duplicates its node
     topology (1 control-plane + 2 workers) and needs to stay in sync if
     either changes.
  2. Relative `file()` paths were off by one directory level (`../../` where
     `../../../` was needed from `envs/local-kind/`) for both
     `kafka-values.yaml` and the faust-processor chart path.
- **Verified end-to-end**: destroyed the manually-created cluster, ran
  `terraform apply` from a clean slate — Kafka came up healthy on the first
  try (the single-broker `overrideConfiguration` fix from the faust-processor
  work held). Hit one self-inflicted race (ran `terraform apply` before
  `kind load docker-image` had actually finished loading the images in the
  background, so the first `helm_release.faust_processor` timed out waiting
  for a pod that couldn't pull its image yet) — `helm uninstall` + re-apply
  fixed it once the images were actually present. After that: `terraform
  plan` reports zero drift, and a full pipeline run (`helm install` the
  telemetry-generator chart with fault injection on) produced **exactly
  matching raw/processed offsets again (36065 == 36065)**.
- `.terraform.lock.hcl` is committed (not gitignored — despite our
  `.gitignore`'s Terraform section previously excluding it, which was wrong;
  Terraform's own `init` output explicitly says to commit it for
  reproducible provider version pinning across machines).
- The kind-provider-written kubeconfig file (`<cluster>-config`) is
  gitignored — it's cluster credentials, same reasoning as any kubeconfig.

**Terraform, AWS EKS env** (`infra/terraform/envs/aws-eks/` +
`infra/terraform/modules/{vpc,eks,iam}/`): written and `terraform validate`d
against the real `terraform-aws-modules/{vpc,eks}/aws` registry modules
(v5.x / v20.x — `terraform init` successfully resolved and downloaded both),
but **never applied** — `terraform plan` fails cleanly on missing AWS
credentials, which is the expected/desired state until the actual EKS
verification run happens (requires explicit sign-off per CLAUDE.md's
real-money-operations rule). Cost-conscious choices baked in: `single_nat_gateway
= true`, SPOT capacity for the node group, `t3.medium` x2. `modules/iam`
sets up one IRSA role (CloudWatch Logs write, via the AWS-managed policy —
noted inline that a longer-lived deployment should scope this down) as a
concrete example of the IRSA pattern, not a placeholder. No remote state
backend configured (deliberate — this env is only ever up briefly under
supervision; noted inline to add an S3+DynamoDB backend first if that ever
changes).

**GitHub Actions CI** (`.github/workflows/{telemetry-generator,faust-processor}.yml`):
path-filtered triggers (only run when that app's files change), `test` job
(pytest) gates a `build-and-push` job (Docker Buildx → GHCR, tagged by
commit SHA + `latest`, only on push to `main`, not PRs). Stops at push —
deployment is ArgoCD's job (Day 8-9), not CI's.
- Added real unit tests, not placeholders: `apps/faust-processor/tests/`
  covers `validate()` (including the "real FastF1 data hits 104% throttle,
  must not be flagged" case), `apps/telemetry-generator/tests/` covers the
  fault-injection probability logic and the NaN/None-handling helpers. All
  12 pass locally. **Not yet verified against a real GitHub Actions run** —
  nothing has been pushed to the `origin` remote this session (everything
  so far is local, uncommitted, per the "not committing until asked"
  instruction) — only local `pytest` and offline YAML syntax checks so far.

**Files**: `infra/helm/{telemetry-generator,faust-processor}/**`,
`infra/terraform/{envs,modules}/**`, `.github/workflows/{telemetry-generator,faust-processor}.yml`,
`apps/{telemetry-generator,faust-processor}/tests/**`, `.gitignore` (lock
file + kind-provider kubeconfig fixes).

---

## Week 2 start — `apps/faust-processor`

**What**: a long-running [faust-streaming](https://github.com/faust-streaming/faust)
worker that consumes `f1.telemetry`, validates each record against
plausibility bounds, computes two per-driver derived features
(`speed_delta_kph`, `out_of_order`), republishes to `f1.telemetry.processed`,
and exposes Prometheus metrics on `/metrics` (port 6066).

**Design decisions**:
- `faust-streaming` (the maintained community fork), not the original
  `faust` package — same reasoning as picking `confluent-kafka` earlier:
  use the actively-maintained option.
- Config via env vars only, no CLI flags — Faust's own `worker` subcommand
  owns argv, so a custom argparse layer (like `telemetry-generator` has)
  would conflict.
- Faust Table state uses `store="memory://"` — avoids a RocksDB build
  dependency in the Docker image; the tradeoff is state resets on pod
  restart, acceptable for a demo, called out in the README as a known
  limitation.
- Validation bounds were set by looking at real data, not guessing: FastF1's
  own throttle readings hit 104% in practice (confirmed in the Day 1-2
  dry-run), so the threshold is 110%, not a naive 100% cap — injected faults
  overshoot by so much (+1000 minimum) that they're still caught regardless.
- `/metrics` is served from Faust's own built-in web server (`@app.page`)
  rather than standing up a second HTTP server/thread — one port, less code.

**Two real bugs hit and fixed while verifying this end-to-end** (both are
now permanent parts of `infra/helm/kafka-values.yaml`, not just today's
workaround):

1. **Single-broker Kafka can't run consumer groups out of the box.**
   Kafka's internal `__consumer_offsets` topic defaults to replication
   factor 3 regardless of broker count; with our single-broker dev cluster
   that can never be satisfied, so the topic never gets created and every
   consumer group hangs forever on `GroupCoordinatorNotAvailableError`.
   First attempted fix used `controller.config` to set
   `offsets.topic.replication.factor: 1` — this actually made things worse:
   `controller.config` *replaces* the chart's auto-generated server.properties
   wholesale rather than merging, which silently dropped `process.roles` and
   broke KRaft storage formatting entirely (`kafka-storage.sh format` exited
   1 with no visible error until re-run with `BITNAMI_DEBUG=true`). The
   correct key is `controller.overrideConfiguration`, which merges on top of
   the auto-generated config instead of replacing it.
2. **Faust's `/metrics` page 500'd**: `prometheus_client.CONTENT_TYPE_LATEST`
   already includes `charset=utf-8`, and Faust's `Response` wrapper rejects
   a `content_type` that already has a charset in it. Fixed by passing plain
   `"text/plain"` instead.

**Known follow-up, not fixed today**: `telemetry-generator`'s injected
`delay` fault sleeps 3-10 real seconds per occurrence, uncorrelated to
`--speed` — fine at low fault rates (used 0.001-0.002 here) but makes
`--fault-rate` above ~1% impractically slow for a full-grid replay. Worth
scaling the delay by `--speed` too if this becomes annoying.

**Verified**: ran `telemetry-generator --inject-faults` in-cluster while
`faust-processor` was live-consuming. At every offset check — including
mid-stream, not just after the producer finished — `f1.telemetry` and
`f1.telemetry.processed` had **exactly equal** offsets (e.g. 68670 == 68670):
zero message loss, zero duplication. Confirmed via `kafka-console-consumer`
that `is_valid:false` correctly fires on injected `out_of_range` values
(`validation_errors: ["speed_out_of_range"]`) and `out_of_order:true`
correctly fires on injected `delay` values. Confirmed `/metrics` updates
live (`f1_telemetry_records_total{driver_code="LEC"} 20859` mid-run) via
`kubectl port-forward` — plain HTTP through port-forward works fine, unlike
the Kafka protocol itself (see Day 1-2 note on `advertised.listeners`).

**Files**: `apps/faust-processor/src/{config,models,validation,metrics,app}.py`,
`Dockerfile`, `requirements.txt`, `README.md`;
`infra/helm/kafka-values.yaml` (replication-factor fix).

---

## Week 1, Day 1-2 (cont.) — local `kind` cluster + Kafka, verified end-to-end

**What**: stood up a local 3-node `kind` cluster (`infra/kind/kind-config.yaml`)
and deployed Kafka via the Bitnami Helm chart (`infra/helm/kafka-values.yaml`,
KRaft mode, single combined controller+broker node, PLAINTEXT, no
persistence tuning beyond a small PVC) into a new `pipeline` namespace.
Captured the whole sequence in `scripts/setup-local-cluster.sh` /
`teardown-local-cluster.sh` so it's one command instead of re-deriving it.

**Toolchain gap**: no Homebrew on the machine. Installed it (needed sudo,
had the user run the official installer themselves since it prompts
interactively), then `brew install kind helm`.

**Two real-world gotchas hit and fixed**:
1. **Bitnami image 404s.** The chart's default `image.repository`
   (`bitnami/kafka`) no longer resolves — Broadcom discontinued free
   rolling image tags on `docker.io/bitnami/*` in August 2025. Fixed by
   overriding `image.repository: bitnamilegacy/kafka` (the frozen last-free
   snapshot) in `kafka-values.yaml`. This image won't get further updates;
   fine for local dev, called out inline in the values file as a caveat for
   anyone reviewing this later.
2. **`advertised.listeners` blocks host access.** The chart advertises
   `kafka-controller-0.kafka-controller-headless.pipeline.svc.cluster.local`,
   which isn't resolvable from the host even through `kubectl port-forward`
   (the initial connection succeeds, but the client is then redirected to
   that unreachable address for actual produce requests and hangs).
   Rather than fighting listener/advertised-address config for host access,
   validated end-to-end by building the `telemetry-generator` image,
   `kind load docker-image`-ing it in, and running it as a one-off in-cluster
   pod against `kafka.pipeline.svc.cluster.local:9092` — which also matches
   how it'll actually be deployed later (Helm, in-cluster), so this wasn't a
   detour.

**Verified**: in-cluster run (`--drivers VER,HAM --speed 20000`) emitted
72,130 records; `kafka-get-offsets.sh` on the broker confirmed the topic's
end offset is exactly 72130 — every message the generator sent was
persisted.

**Files**: `infra/kind/kind-config.yaml`, `infra/helm/kafka-values.yaml`,
`scripts/setup-local-cluster.sh`, `scripts/teardown-local-cluster.sh`.

---

## Week 1, Day 1-2 — `apps/telemetry-generator`

**What**: a replay bridge that pulls one historical F1 session via
[FastF1](https://docs.fastf1.dev/) and republishes its car telemetry onto
Kafka on a paced timeline, simulating a live feed.

**Why FastF1 over OpenF1**: CLAUDE.md originally named OpenF1 as the replay
source. Switched to FastF1 because it gives per-car telemetry (Speed,
Throttle, Brake, nGear, RPM, DRS) at ~3-4Hz with a simple pandas-based API
and local caching, vs. OpenF1's more session/lap-level data plus a live
websocket we don't need (we don't want the demo depending on a live race
weekend — reproducible historical replay is preferable for recording and
testing).

**Design decisions**:
- Replay speed is a configurable multiplier (`--speed`, default 20x) rather
  than strict real-time, so dev iteration and demo recordings don't take
  1.5-2 hours per race.
- Real telemetry is "clean" and unlikely to naturally trip the Prometheus
  alert rules planned for later. Added an opt-in `--inject-faults` mode that
  randomly produces either an out-of-range value (`speed_kph`/`rpm` spiked)
  or a delayed record (held before publishing), so the alerting pipeline has
  something real to catch on demand.
- The generator supports `--dry-run` (prints JSON to stdout instead of
  publishing) so its FastF1/replay logic could be validated today without a
  Kafka broker existing yet. Kafka isn't wired up until the local `kind` +
  Bitnami Kafka Helm chart step.
- Kafka client: `confluent-kafka` (prebuilt wheels on macOS/Linux, no manual
  librdkafka install needed).
- Message key = driver number (partition affinity, preserves per-driver
  ordering); topic defaults to `f1.telemetry`.

**Verified**: `python -m src.main --dry-run --drivers VER --speed 100000`
pulled the full 2023 Bahrain GP session (20 drivers) and streamed correctly
ordered records. `--inject-faults --fault-rate 0.5` confirmed both fault
types fire: `delay` (gap between consecutive `emitted_at` timestamps) and
`out_of_range` (`speed_kph` jumping to an implausible value).

**Not done yet**: no Kafka broker running, so the Kafka publish path
(`KafkaSink`) is implemented but untested end-to-end.

**Files**: `apps/telemetry-generator/src/{config,fastf1_source,faults,sinks,replay,main}.py`,
`Dockerfile`, `requirements.txt`, `README.md`.
