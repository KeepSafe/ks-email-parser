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
| Task 2b hooks/CI/Makefile/README | Partial | Update Makefile/README/Travis and add CircleCI for a library/CLI. Lightweight standard test aliases are present. Service-style hooks are not required for this repo. |
| Task 2c mypy stabilization | Not applicable | The repo has no existing mypy contract; adding a new type-checking surface is out of scope for this no-stack migration. |
| Task 3 msgpack/redis/asynctest/nosetests | Partial | No msgpack, redis, or asynctest usage. Replace `nosetests` with `pynose`. |
| Task 4 asyncio/aiohttp modernization | Partial | No aiohttp. Modernize the CLI's asyncio execution path for Python 3.11. |
| Task 4c async test harness modernization | Not applicable | No reusable async test harness exists. |
| Task 5 Gunicorn/Docker local infra | Not applicable | This repo is not service-shaped and has no local backing services. |
| Task 6 deterministic service requirements | Partial | Keep `requirements.txt` aligned to exact runtime pins for consumers; no ansible/service requirements build pipeline is added here. |

## Dependency Notes

- Baseline Python 3.11 install failed because `pystache==0.5.4` uses the removed `use_2to3` build path.
- Runtime dependencies are exact pins in `pyproject.toml` and mirrored in `requirements.txt`.
- `pystache` is upgraded to a Python 3.11-installable release.
- `Markdown` is upgraded to `3.10.2`; repo extensions now use the Markdown 3 inline/block processor registration APIs.
- `inlinestyler` is upgraded to `0.2.5` and `lxml` to `6.1.1`; the renderer adds a narrow
  `CSSSelector.evaluate` compatibility alias for inlinestyler's legacy selector calls and normalizes output so golden
  fixtures remain stable.
- `parse` is upgraded to `1.22.1`.
- Dev/test pins are latest observed on 2026-07-21 except where already current: `build==1.5.0`,
  `coverage==7.15.2`, `flake8==7.3.0`, `flake8-pyproject==1.2.4`, `pynose==1.5.5`,
  `pyupgrade==3.21.2`, and `twine==6.2.0`.
- Beautiful Soup 4.15.0 retains the APIs deprecated in 4.13.0 for this release and fixes an `html.parser` crash on
  Python 3.11.13. This repo uses the current `BeautifulSoup` constructor and `find_all` APIs, and golden output is stable.
- lxml 6.1.1 contains security and link-attribute fixes; the XML fallback and HTML rendering fixtures remain stable.
- parse 1.22.1 expands zero-precision float parsing. Existing parser behavior and fixtures remain stable.
- coverage 7.15.0 through 7.15.2 add reporting fixes and `--keep-combined`; the existing pynose coverage invocation,
  minimum threshold, and XML output remain compatible.
- `msgpack` is not a direct dependency, source/test import, or installed transitive dependency. `libks` currently pins
  `msgpack==1.1.2` and centralizes compatibility through `msgpack_*_compat*` helpers, but this repo has no msgpack
  call sites that need those conventions. `make lint` includes `check-msgpack` to catch accidental source/test imports.

## Latest Dependency Audit

Checked with `venv/bin/pip index versions` and local install/test proof on 2026-07-21.

| Dependency | Selected pin | Latest observed | Reason retained |
| --- | --- | --- | --- |
| `beautifulsoup4` | `4.15.0` | `4.15.0` | Latest observed; fixture proof passes. |
| `Markdown` | `3.10.2` | `3.10.2` | Latest observed; compatibility fixes preserve fixture output. |
| `cssutils` | `2.11.1` | `2.15.0` | Latest safe pin. `2.13.0`, `2.14.0`, and `2.15.0` import-fail locally with `ModuleNotFoundError: No module named 'encutils'` despite installing `encutils==1.0.0`. |
| `inlinestyler` | `0.2.5` | `0.2.5` | Latest observed; compatibility alias preserves renderer behavior with latest `lxml`. |
| `lxml` | `6.1.1` | `6.1.1` | Latest observed; golden fixture proof passes. |
| `parse` | `1.22.1` | `1.22.1` | Latest observed; fixture proof passes. |
| `pystache` | `0.6.8` | `0.6.8` | Latest observed; fixes Python 3.11 `use_2to3` install blocker. |
| `coverage` | `7.15.2` | `7.15.2` | Latest observed; unit coverage reporting remains compatible. |

## CI Notes

- `.circleci/config.yml` follows the `python311-service-upgrade-stack` sample intent with valid CircleCI 2.1
  `executors`/`commands`, `cimg/python:3.11.13`, `prepare_cache`, `lint`, and `test` jobs.
- CircleCI runs `make ci-dev-install`, `make lint`, and `make test-only`; test results and coverage XML artifacts are
  stored from `build/test` and `build/coverage/coverage.xml`.
- The config keeps the sample terminal cache fallback keys (`v3-pip-` and `v3-venv-`) and the non-fatal Codecov upload
  step.
- The existing Travis file remains for historical compatibility until the repo owner removes it.

## Egress Policy

Default verification is local-only. Tests and CLI smoke operate on committed fixtures and temporary directories. No production,
paid provider, or public external service calls are part of behavior proof.

## Known Gaps

- TODO: run the skill's final two-consecutive-clean-review cycle after remote CI reports on the next push.
- TODO: downstream `email-service`, `emails`, and Ansible packaging must run their own Python 3.11 proof after
  consuming the migrated package.
- The published package artifact is not uploaded in this migration session.

## Verification Evidence

Captured on branch `python311-upgrade` in the migration worktree.

| Command | Result | Notes |
| --- | --- | --- |
| `python3.11 -m venv venv` | Pass | Created the Python 3.11 local environment. |
| `venv/bin/pip install -e '.[tests,devtools]'` on the pre-migration setup metadata | Fail | Baseline failed because `pystache==0.5.4` uses removed `use_2to3` build metadata. |
| `make clean` | Pass | Removed local build/test artifacts before clean install. |
| `make dev` | Pass | Installed runtime and dev/test extras from `pyproject.toml`. |
| `make lint` | Pass | `flake8 7.3.0` with `flake8-pyproject 1.2.4`. |
| `make test` | Pass | `86` tests, includes golden fixture comparisons, CLI smoke, and empty-render failure regression. |
| `venv/bin/python -m compileall email_parser tests` | Pass | Source and tests compile under Python 3.11. |
| `venv/bin/python -c "import email_parser; print(email_parser.Parser)"` | Pass | Import smoke returned `<class 'email_parser.Parser'>`. |
| `venv/bin/ks-email-parser --version` | Pass | CLI metadata smoke returned `1.0.0`. |
| `venv/bin/pip check` | Pass | No broken requirements found. |
| `venv/bin/python -m build` | Pass | Built `ks_email_parser-1.0.0.tar.gz` and `ks_email_parser-1.0.0-py3-none-any.whl`. |
| `venv/bin/twine check dist/*` | Pass | Both the sdist and wheel metadata passed validation. |
| Updated dependency import/version smoke | Pass | Imported Beautiful Soup 4.15.0, lxml 6.1.1, parse 1.22.1, coverage 7.15.2, and `email_parser.Parser`. |
| `venv/bin/pyupgrade --keep-percent-format --py36-plus ... --py311-plus` | Pass | Ladder completed across `email_parser/*.py` and `tests/*.py`. |
| `venv/bin/pip list --format=freeze` | Pass | No installed `msgpack` distribution; latest selected dependency set installed. |
| `venv/bin/pip install cssutils==2.13.0`, `2.14.0`, `2.15.0` import checks | Fail | Later cssutils releases install but fail `import cssutils` because no importable `encutils` module is present. |
| `ruby -e "require 'yaml'; YAML.load_file('.circleci/config.yml'); puts 'ok'"` | Pass | CircleCI config parses as YAML locally. |
| `circleci config validate .circleci/config.yml` | Pass | CircleCI CLI reported the config file is valid after moving sample-style reuse into valid `executors` and `commands` sections. |

`make test` still prints legacy fixture warnings for intentionally malformed XML fallback cases; those warnings are covered by
existing tests and do not fail the suite.
