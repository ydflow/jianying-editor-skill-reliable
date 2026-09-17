# Security Policy

## Supported Versions

Security fixes are provided for the latest `main` branch.

## Reporting a Vulnerability

Please report vulnerabilities privately by opening a GitHub Security Advisory in this repository.

Include:

- Affected component or file path
- Reproduction steps / proof of concept
- Impact assessment
- Suggested remediation (if available)

Do not disclose details publicly until a fix is available.

## Response Targets

The maintainers will acknowledge and triage valid reports on a best-effort basis.

## Destructive-operation boundary

- Environment diagnostics are read-only by default.
- Replacing an existing draft requires an explicit `overwrite=True` and a successful backup.
- Automatic export is blocked on unverified JianYing versions unless the caller explicitly forces it.
