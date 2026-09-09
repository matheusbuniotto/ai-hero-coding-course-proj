# Contributing

## Local setup

```bash
uv sync --all-groups
uvx prek install
```

This installs `ruff` (lint + format), `ty` (type checking), and `detect-secrets` as git pre-commit hooks. They run automatically on `git commit` and block the commit on any violation.

To run the full suite on demand:

```bash
uvx prek run --all-files
```

CI runs the same suite on every pull request.

## Secrets baseline

New findings from `detect-secrets` must be reviewed and either removed or, if they are false positives, added to the baseline:

```bash
uv run detect-secrets scan --baseline .secrets.baseline
```

## Code Standarts

- Pythonic code, do not try to force non-pythonic behaviour into python synxta.
- Beutiful code is a must
- Do NOT overcomment, code must be self-explanatory
- Follow the zen of python for python code.
