# Developer Assurance Baseline

Every deployable repository must commit its dependency lockfiles, declare a reproducible local build command, run a secret scan, produce language-appropriate tests and publish an SBOM/provenance record with a release candidate. Third-party action references and dependencies are reviewed and pinned according to the Ministry’s supply-chain policy before production promotion.

A green unit-test run is not a deployment, integration or conformance claim. Genuine integration verification requires the authorised non-production target and masked evidence defined in the programme integration-gate policy.
