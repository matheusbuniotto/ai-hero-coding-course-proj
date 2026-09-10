# Contributing

## Local setup

```bash
make install
uvx prek install
```

This installs `ruff` (lint + format), `ty` (type checking), and `detect-secrets` as git pre-commit hooks. They run automatically on `git commit` and block the commit on any violation.

To run the full suite on demand:

```bash
uvx prek run --all-files
```

CI runs the same suite on every pull request.

## Running the app

```bash
make dev   # API on :8000 and the workspace UI on :5173, Ctrl-C stops both
```

`make api` and `make ui` run either half on its own.

Open the UI at <http://localhost:5173>. Its dev server proxies `/me`, `/auth`, `/workspace`
and `/workspaces` to the API, so the magic-link session cookie stays same-origin. Sign in
from the UI's origin: the magic link is printed to the API's console and opening it lands
you back in the UI.

To skip copying the link out of the console every time, set `ICM_DEV_AUTH=1` before
starting the API (`ICM_DEV_AUTH=1 make dev`). The login page then also offers a "Dev sign
in" form that signs you straight in as any email, no magic link involved. It 404s unless
the flag is set, so it can't end up live by accident.

Both halves take their port from one variable, so `make dev API_PORT=8123` moves the API
and repoints the proxy at it together.

## Tests and checks

```bash
make test    # pytest + vitest
make check   # ruff, ty, and tsc
```

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
