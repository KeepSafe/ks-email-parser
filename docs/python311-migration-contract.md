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
venv/bin/pyupgrade --keep-percent-format --py36-plus email_parser/*.py tests/*.py
venv/bin/pyupgrade --keep-percent-format --py37-plus email_parser/*.py tests/*.py
venv/bin/pyupgrade --keep-percent-format --py38-plus email_parser/*.py tests/*.py
venv/bin/pyupgrade --keep-percent-format --py39-plus email_parser/*.py tests/*.py
venv/bin/pyupgrade --keep-percent-format --py310-plus email_parser/*.py tests/*.py
venv/bin/pyupgrade --keep-percent-format --py311-plus email_parser/*.py tests/*.py
```

Fixture/CLI compatibility is covered by the unit suite:

- Existing golden fixture tests compare rendered `email.subject`, `email.text`, and `email.html` outputs.
- `tests/test_cli_smoke.py` runs the CLI in a temporary email tree and compares generated outputs against committed
  fixtures.

## `$python311-service-upgrade-stack` Task Mapping

| Skill task | Applicability | ks-email-parser mapping |
| --- | --- | --- |
| Task 1 packaging/Python 3.11/dependency audit/pyupgrade | Applicable | Replace setup metadata with `pyproject.toml`, pin Python 3.11, bump version, pin compatible runtime deps, run the pyupgrade ladder. |
| Task 2a formatting/flake8 alignment | Applicable | Keep 120-character Flake8 policy in `pyproject.toml` and run `make lint`. |
| Task 2b hooks/CI/Makefile/README | Partial | Update Makefile, README, and Travis for a library/CLI. Lightweight standard test aliases are present. Service-style hooks/CircleCI are not required for this repo. |
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

## Not Upgraded To Latest (3.11 Compatible)

Checked with `venv/bin/pip index versions` on 2026-05-13.

| Dependency | Selected pin | Latest observed | Reason retained |
| --- | --- | --- | --- |
| `Markdown` | `2.6.11` | `3.10.2` | Existing parser extensions use the legacy Markdown 2.x extension API; fixture output is preserved with the current pin. |
| `cssutils` | `2.11.1` | `2.15.0` | Selected compatible 2.x pin works with `inlinestyler` and golden fixtures; no migration need for a later minor. |
| `inlinestyler` | `0.2.1` | `0.2.5` | Existing pin installs under Python 3.11 and preserves inline CSS fixture output. |
| `lxml` | `4.9.4` | `6.1.0` | Last 4.x line preserves downstream `<5` expectations while providing Python 3.11 wheels. |
| `parse` | `1.19.0` | `1.22.0` | Kept close to downstream email-service/content-validator compatibility while remaining Python 3.11-compatible. |

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
| `make test` | Pass | `86` tests, includes golden fixture comparisons, CLI smoke, and empty-render failure regression. |
| `venv/bin/python -m compileall email_parser tests` | Pass | Source and tests compile under Python 3.11. |
| `venv/bin/python -c "import email_parser; print(email_parser.Parser)"` | Pass | Import smoke returned `<class 'email_parser.Parser'>`. |
| `venv/bin/ks-email-parser --version` | Pass | CLI metadata smoke returned `1.0.0`. |
| `venv/bin/pip check` | Pass | No broken requirements found. |
| `venv/bin/python -m build` | Pass | Built `ks_email_parser-1.0.0.tar.gz` and `ks_email_parser-1.0.0-py3-none-any.whl`. |
| `venv/bin/pyupgrade --keep-percent-format --py36-plus ... --py311-plus` | Pass | Ladder completed across `email_parser/*.py` and `tests/*.py`. |

`make test` still prints legacy fixture warnings for intentionally malformed XML fallback cases; those warnings are covered by
existing tests and do not fail the suite.
