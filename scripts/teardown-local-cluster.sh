#!/usr/bin/env bash
# Tear down the local kind cluster (no cost, no confirmation needed —
# unlike the AWS EKS validation run, which always requires sign-off first).
set -euo pipefail

kind delete cluster --name f1-platform
