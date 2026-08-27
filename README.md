# Blue Economy Developer Platform

This repository supplies reusable, language-specific build and assurance workflows for Blue Economy Platform repositories. It is intentionally independent from business-domain code. It standardises reproducible validation, dependency lockfiles, SBOM generation, secret scanning, dependency vulnerability scanning and language quality gates.

The workflow files are reusable building blocks; an application repository becomes compliant only when it invokes the relevant workflows and produces a successful run against its own committed source.

## What the reusable workflows actually do

All third-party actions are pinned to full commit SHAs with a trailing version comment.

- **Reusable Go Validation** (`reusable-go.yml`): `go mod download`, `go vet`, race-enabled `go test`, a `govulncheck` dependency vulnerability scan, SPDX-JSON SBOM generation via Anchore `sbom-action` (Syft) and verified-secret scanning via TruffleHog.
- **Reusable Rust Validation** (`reusable-rust.yml`): `cargo fmt --check`, `cargo clippy -D warnings`, `cargo test --locked`, a `cargo audit` dependency vulnerability scan, plus the same SBOM and secret-scanning steps.
- **Reusable Python Validation** (`reusable-python.yml`): `compileall` source compilation, `pytest -x` whenever a test suite exists in the calling repository, `ruff check` and `bandit` when their configuration is present, advisory (non-blocking) `mypy` when configured, and a `pip-audit` dependency vulnerability scan when a dependency manifest exists, plus the same SBOM and secret-scanning steps. Tool steps skip gracefully only when the tool or its configuration is genuinely absent from the calling repository.
- **Reusable TypeScript Validation** (`reusable-typescript.yml`): `pnpm install --frozen-lockfile`, `pnpm lint`, `pnpm test`, `pnpm build`, a `pnpm audit` dependency vulnerability scan, plus the same SBOM and secret-scanning steps.

SBOMs are produced as SPDX-JSON workflow artifacts; secret scanning fails the run on verified findings. Governance templates under `governance/` and `ci/github-actions/` are kept byte-identical to the installed workflows; the Repository Governance workflow fails if they drift.
