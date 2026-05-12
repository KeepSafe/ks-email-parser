# ks-email-parser Python 3.11 Migration Contract

## Repo Classification

`ks-email-parser` is a no-stack library/CLI tool. It exposes the `email_parser` Python package and the
`ks-email-parser` console command. It has no Paste/Gunicorn service runtime, worker process, Docker-backed local
dependencies, or production service endpoints.

## Branch and Write Scope

- Worktree: `/Users/olmos/keepsafe/repos/worktrees/ks-email-parser-python-upgrade`
- Branch: `python311-upgrade`
- First write scope: this contract, fixture/CLI compatibility proof, Python 3.11 packaging, Makefile/CI workflow, and
  focused runtime compatibility fixes.

## Public Surfaces

- Python package import: `import email_parser`
- Public object used by callers: `email_parser.Parser`
- Console script: `ks-email-parser = email_parser.cmd:main`
- Behavior-sensitive outputs: generated `.subject`, `.text`, and `.html` files under the configured destination.
- Config command: `ks-email-parser config placeholders`

## Downstream Consumers

- `email-service` declares `ks-email-parser` as an internal dependency and vendors an older source copy under
  `email-service/src/ks-email-parser`.
- `emails` documents and invokes the `ks-email-parser` CLI to render email assets.
- `ansible/update_email_service.yml` packages `ks-email-parser` for email-service deployment.

## Python 3.11 Target

- `.python-version`: `3.11.13`
- `pyproject.toml`: `requires-python = ">=3.11,<3.12"`
- Package version: `1.0.0` (next major from the pre-migration `0.3.2` baseline).

## Proof Commands

Run from the worktree root:

```bash
make clean
make dev
make lint
make test
venv/bin/python -m compileall email_parser tests
venv/bin/python -c "import email_parser; print(email_parser.Parser)"
venv/bin/ks-email-parser --version
```

Fixture/CLI compatibility is covered by the unit suite:

- Existing golden fixture tests compare rendered `email.subject`, `email.text`, and `email.html` outputs.
- `tests/test_cli_smoke.py` runs the CLI in a temporary email tree and compares generated outputs against committed
  fixtures.

## `$python311-service-upgrade-stack` Task Mapping

| Skill task | Applicability | ks-email-parser mapping |
| --- | --- | --- |
| Task 1 packaging/Python 3.11/dependency audit/pyupgrade | Applicable | Replace setup metadata with `pyproject.toml`, pin Python 3.11, bump version, pin compatible runtime deps, run focused code modernization. |
| Task 2a formatting/flake8 alignment | Applicable | Keep 120-character Flake8 policy in `pyproject.toml` and run `make lint`. |
| Task 2b hooks/CI/Makefile/README | Partial | Update Makefile, README, and Travis for a library/CLI. Service-style hooks/CircleCI are not required for this repo. |
| Task 2c mypy stabilization | Not applicable | The repo has no existing mypy contract; adding a new type-checking surface is out of scope for this no-stack migration. |
| Task 3 msgpack/redis/asynctest/nosetests | Partial | No msgpack, redis, or asynctest usage. Replace `nosetests` with `pynose`. |
| Task 4 asyncio/aiohttp modernization | Partial | No aiohttp. Modernize the CLI's asyncio execution path for Python 3.11. |
| Task 4c async test harness modernization | Not applicable | No reusable async test harness exists. |
| Task 5 Gunicorn/Docker local infra | Not applicable | This repo is not service-shaped and has no local backing services. |
| Task 6 deterministic service requirements | Partial | Keep `requirements.txt` aligned to exact runtime pins for consumers; no ansible/service requirements build pipeline is added here. |

## Dependency Notes

- Baseline Python 3.11 install failed because `pystache==0.5.4` uses the removed `use_2to3` build path.
- Runtime dependencies are exact pins in `pyproject.toml`.
- `pystache` is upgraded to a Python 3.11-installable release.
- `lxml` is upgraded within the `<5` family to preserve downstream expectations while using Python 3.11 wheels.
- `parse` remains pinned near the downstream email-service/content-validator compatibility range.

## Egress Policy

Default verification is local-only. Tests and CLI smoke operate on committed fixtures and temporary directories. No production,
paid provider, or public external service calls are part of behavior proof.

## Known Gaps

- Downstream `email-service` must still run its own Python 3.11 proof after consuming the migrated package.
- The published package artifact is not uploaded in this migration session.

## Verification Evidence

Captured on branch `python311-upgrade` in the migration worktree.

| Command | Result | Notes |
| --- | --- | --- |
| `python3.11 -m venv venv` | Pass | Created the Python 3.11 local environment. |
| `venv/bin/pip install -e '.[tests,devtools]'` on the pre-migration setup metadata | Fail | Baseline failed because `pystache==0.5.4` uses removed `use_2to3` build metadata. |
| `make clean` | Pass | Removed local build/test artifacts before clean install. |
| `make dev` | Pass | Installed runtime and dev/test extras from `pyproject.toml`. |
| `make lint` | Pass | `flake8 7.3.0` with `flake8-pyproject 1.2.3`. |
| `make test` | Pass | `85` tests, `79%` coverage. Includes golden fixture comparisons and CLI smoke. |
| `venv/bin/python -m compileall email_parser tests` | Pass | Source and tests compile under Python 3.11. |
| `venv/bin/python -c "import email_parser; print(email_parser.Parser)"` | Pass | Import smoke returned `<class 'email_parser.Parser'>`. |
| `venv/bin/ks-email-parser --version` | Pass | CLI metadata smoke returned `1.0.0`. |
| `venv/bin/pip check` | Pass | No broken requirements found. |
| `venv/bin/python -m build` | Pass | Built `ks_email_parser-1.0.0.tar.gz` and `ks_email_parser-1.0.0-py3-none-any.whl`. |

`make test` still prints legacy fixture warnings for intentionally malformed XML fallback cases; those warnings are covered by
existing tests and do not fail the suite.
