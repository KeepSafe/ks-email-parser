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

- `email-service` declares the published `ks-email-parser==1.0.1` package in `pyproject.toml`; the Python 3.11
  branch no longer vendors a source copy.
- `emails` documents and invokes the `ks-email-parser` CLI to render email assets.
- Ansible packages `ks-email-parser` through the email-service deployment roles.

## Python 3.11 Target

- `.python-version`: `3.11.13`
- `pyproject.toml`: `requires-python = ">=3.11,<3.12"`
- Package version: `1.0.1` (the current patch release on the Python 3.11 line).

## Release Branch Policy

- `master` remains the Python 3.6 production line while both runtimes coexist.
- `python311-upgrade` is the live Python 3.11 release line, and all 1.x tags are created from CI-green commits on
  this branch.
- The Python 3.11 branch merges into `master` only after the production rollout is complete; merging to `master` is
  not a prerequisite for tagging or publishing a 1.x release.

## Proof Commands

Run from the worktree root:

```bash
make clean
make dev
make lint
CI=1 make test
venv/bin/pip check
venv/bin/python -m compileall -q email_parser tests
venv/bin/python -c "import email_parser; print(email_parser.Parser)"
venv/bin/ks-email-parser --help
venv/bin/ks-email-parser --version
rm -rf dist && venv/bin/python -m build .
venv/bin/twine check dist/*
circleci config validate .circleci/config.yml
circleci config validate --next .circleci/config.yml
circleci config process .circleci/config.yml >/tmp/ks-email-parser-circleci-processed.yml
ruby -e "require 'yaml'; YAML.load_file('.travis.yml'); puts 'ok'"
```

The one-time pyupgrade ladder from `--py36-plus` through `--py311-plus` was completed during the migration. Pyupgrade
is not retained as an installable project dependency after that proof completed.

Fixture/CLI compatibility is covered by the unit suite:

- Existing golden fixture tests compare rendered `email.subject`, `email.text`, and `email.html` outputs.
- `tests/test_cli_smoke.py` runs the CLI in a temporary email tree and compares generated outputs against committed
  fixtures. It also proves `config placeholders` writes `src/placeholders_config.json` relative to the email root and
  that unsupported config commands fail without writing a config file.
- Focused regression tests preserve percent-encoded URL components in absolute and relative Markdown image sources,
  while continuing to normalize encoded Mustache placeholder spaces.
- Renderer regressions prove that CSS-inlined and authored paragraph attributes survive single-element paragraph
  formatting, with the attribute-free and no-tracking output shapes unchanged.

## `$python311-service-upgrade-stack` Task Mapping

| Skill task | Applicability | ks-email-parser mapping |
| --- | --- | --- |
| Task 1 packaging/Python 3.11/dependency audit/pyupgrade | Applicable | Replace setup metadata with `pyproject.toml`, pin Python 3.11, bump version, pin compatible runtime deps, run the pyupgrade ladder. |
| Task 2a formatting/flake8 alignment | Applicable | Keep 120-character Flake8 policy in `pyproject.toml` and run `make lint`. |
| Task 2b hooks/CI/Makefile/README | Partial | Update Makefile/README/Travis and add CircleCI for a library/CLI. Travis uses its supported Jammy/Python 3.11.9 runtime while local and CircleCI use 3.11.13. Lightweight standard test aliases are present. Service-style hooks are not required for this repo. |
| Task 2c mypy stabilization | Not applicable | The repo has no existing mypy contract; adding a new type-checking surface is out of scope for this no-stack migration. |
| Task 3 msgpack/redis/asynctest/nosetests | Partial | No msgpack, redis, or asynctest usage. Replace `nosetests` with `pynose` and enforce the no-direct-msgpack-import policy with a fail-closed source scan. |
| Task 4 asyncio/aiohttp modernization | Partial | No aiohttp. Modernize the CLI's asyncio execution path for Python 3.11. |
| Task 4c async test harness modernization | Not applicable | No reusable async test harness exists. |
| Task 5 Gunicorn/Docker local infra | Not applicable | This repo is not service-shaped and has no local backing services. |
| Task 6 deterministic service requirements | Partial | Use the Ansible focal-fossa builder to produce a pypicloud-only, hash-enforced deployment lock for x86_64 and aarch64. Service-specific CI/deployment lock variants remain not applicable. |

## Dependency Notes

- Baseline Python 3.11 install failed because `pystache==0.5.4` uses the removed `use_2to3` build path.
- Runtime dependencies are exact pins in `pyproject.toml`. The generated `requirements/requirements.txt` is a
  pypicloud-only, hash-enforced deployment artifact; it is not an install source for local or cloud CI.
- Isolated builds require `setuptools>=82.0.1` and `wheel>=0.47.0`; the exact minimum backend pair is part of package
  proof so the declared lower bounds are known to accept the project's SPDX metadata.
- `MANIFEST.in` ships the Makefile, generated deployment lock, test modules, and all fixture file types needed to run
  the complete suite from an extracted sdist. Setuptools package discovery still keeps tests and fixtures out of the
  wheel.
- `pystache` is upgraded to a Python 3.11-installable release.
- `Markdown` is upgraded to `3.10.2`; repo extensions now use the Markdown 3 inline/block processor registration APIs.
- `inlinestyler` is upgraded to `0.2.5` and `lxml` to `6.0.2`; the renderer adds a narrow
  `CSSSelector.evaluate` compatibility alias for inlinestyler's legacy selector calls and normalizes output so golden
  fixtures remain stable.
- `parse` is upgraded to `1.22.1`.
- Dev/test pins are latest observed on 2026-07-21 except where already current: `build==1.5.0`,
  `coverage==7.15.2`, `flake8==7.3.0`, `flake8-pyproject==1.2.4`, `pynose==1.5.5`, and `twine==6.2.0`.
- `pyupgrade==3.21.2` was used to complete the required migration ladder, then removed from project extras because it
  is not part of ongoing build, lint, test, or publish workflows.
- The unused `email_parser.link_shortener` prototype was removed instead of adding an undeclared direct `requests`
  dependency. It had no package, test, CLI, or downstream call sites and was never connected to `TextRenderer`.
  `requests` remains an expected transitive dependency of `inlinestyler`; it is not imported directly by this project.
- Beautiful Soup 4.15.0 retains the APIs deprecated in 4.13.0 for this release and fixes an `html.parser` crash on
  Python 3.11.13. This repo uses the current `BeautifulSoup` constructor and `find_all` APIs, and golden output is stable.
- lxml 6.0.2 is Python 3.11-compatible and matches downstream `libks==1.0.12`; the XML fallback and HTML rendering fixtures remain
  stable.
- parse 1.22.1 expands zero-precision float parsing. Existing parser behavior and fixtures remain stable.
- coverage 7.15.0 through 7.15.2 add reporting fixes and `--keep-combined`; the existing pynose coverage invocation,
  minimum threshold, and XML output remain compatible.
- `msgpack` is not a direct dependency, source/test import, or installed transitive dependency. `libks` currently pins
  `msgpack==1.1.2` and centralizes compatibility through `msgpack_*_compat*` helpers, but this repo has no msgpack
  call sites that need those conventions. `make lint` includes the shared KeepSafe recursive-`grep` `check-msgpack`
  convention plus an explicit scanner preflight, so missing scanners and accidental source/test imports both fail.
- `sdiff` and Mistune are not dependencies or imports of this project. A runtime-only environment containing the built
  wheel, local `sdiff==2.0.0` at `3bb941e9f1b209b17abe3b674d453ae829359665`, and Mistune `3.3.4` passes
  `pip check`, imports, and byte-identical fixture rendering without adding either package to this project's metadata.

## Latest Dependency Audit

Checked with `venv/bin/pip index versions` and local install/test proof on 2026-07-21.

| Dependency | Selected pin | Latest observed | Reason retained |
| --- | --- | --- | --- |
| `beautifulsoup4` | `4.15.0` | `4.15.0` | Latest observed; fixture proof passes. |
| `Markdown` | `3.10.2` | `3.10.2` | Latest observed; compatibility fixes preserve fixture output. |
| `cssutils` | `2.11.1` | `2.15.0` | Latest safe pin. `2.13.0`, `2.14.0`, and `2.15.0` import-fail locally with `ModuleNotFoundError: No module named 'encutils'` despite installing `encutils==1.0.0`. |
| `inlinestyler` | `0.2.5` | `0.2.5` | Latest observed; compatibility alias preserves renderer behavior with latest `lxml`. |
| `lxml` | `6.0.2` | `6.1.1` | Required to resolve with downstream `libks==1.0.12`; golden fixture proof passes. |
| `parse` | `1.22.1` | `1.22.1` | Latest observed; fixture proof passes. |
| `pystache` | `0.6.8` | `0.6.8` | Latest observed; fixes Python 3.11 `use_2to3` install blocker. |
| `coverage` | `7.15.2` | `7.15.2` | Latest observed; unit coverage reporting remains compatible. |

## CI Notes

- `.circleci/config.yml` follows the `python311-service-upgrade-stack` sample intent with valid CircleCI 2.1
  `executors`/`commands`, `cimg/python:3.11.13`, `prepare_cache`, `lint`, and `test` jobs.
- CircleCI runs `make ci-dev-install`, `make lint`, and `make test-only`; test results and coverage XML artifacts are
  stored from `build/test` and `build/coverage/coverage.xml`.
- `make ci-dev-install` is cache-aware and installs `.[tests,devtools]` from public package metadata without cleaning a
  restored virtualenv or probing pypicloud. This repo has no private runtime dependency, so no Git preinstall or
  KeepSafe SSH key is required.
- CircleCI `v5` cache checksums include both `pyproject.toml` and the generated deployment lock. The venv restore uses
  only the exact key, preventing stale environments from a broader fallback.
- The existing Travis workflow remains for historical compatibility and explicitly selects Ubuntu Jammy with Python
  3.11.9, the patch release supported in that environment. Travis uses the same public-safe `make ci-dev-install`
  target. `.python-version` and CircleCI remain on Python 3.11.13.

## Egress Policy

Default verification is local-only. Tests and CLI smoke operate on committed fixtures and temporary directories. No production,
paid provider, or public external service calls are part of behavior proof.

## Known Gaps

- TODO: run the skill's final two-consecutive-clean-review cycle after remote CI reports on the next push.
- Email-service PR #439's pending downstream update uses `ks-email-parser==1.0.1`, a combined
  x86_64/aarch64 hash lock, and passing local integration coverage; fresh cloud CI remains a post-push gate.
- The separate `emails` consumer and final Ansible deployment remain downstream rollout responsibilities; the
  email-service Python 3.11 deployment work is tracked in KeepSafe/ansible#545.
- The `1.0.1` wheel is published on internal pypicloud and resolves from the email-service Python 3.11 environment.

## 1.0.0 Verification Evidence

Captured on branch `python311-upgrade` in the migration worktree.

| Command | Result | Notes |
| --- | --- | --- |
| `python3.11 -m venv venv` | Pass | Created the Python 3.11 local environment. |
| `venv/bin/pip install -e '.[tests,devtools]'` on the pre-migration setup metadata | Fail | Baseline failed because `pystache==0.5.4` uses removed `use_2to3` build metadata. |
| `make clean` | Pass | Removed local build/test artifacts before clean install. |
| `make dev` | Pass | Installed runtime and dev/test extras from `pyproject.toml`. |
| Fresh public-only `CI=1 make ci-dev-install` in `/tmp/ks-email-parser-final-proof.d4UDQt` | Pass | Created a new Python 3.11 venv, installed `.[tests,devtools]` from public PyPI, and made no pypicloud probe. |
| Cache-preservation marker plus `CI=1 make ci-env` | Pass | The marker remained in the existing venv, proving the CI bootstrap no longer deletes a restored cache. |
| `make lint` | Pass | `flake8 7.3.0` with `flake8-pyproject 1.2.4`. |
| `make check-msgpack` | Pass | No direct msgpack imports were found in `email_parser` or `tests`. |
| Disposable direct-msgpack-import probe | Pass | `make check-msgpack` printed the matching file and exited nonzero. |
| Disposable missing-`grep` probe | Pass | The target reported that the scanner was unavailable and exited nonzero instead of silently passing. |
| Fresh public-only `CI=1 make test` | Pass | `99` tests, `80%` coverage; includes golden fixtures, CLI/config smokes, empty-render failure, URL encoding, and paragraph-attribute regressions. |
| `venv/bin/python -m compileall email_parser tests` | Pass | Source and tests compile under Python 3.11. |
| `venv/bin/python -c "import email_parser; print(email_parser.Parser)"` | Pass | Import smoke returned `<class 'email_parser.Parser'>`. |
| `venv/bin/ks-email-parser --version` | Pass | CLI metadata smoke returned `1.0.0`. |
| `venv/bin/ks-email-parser config placeholders` in a minimal temporary tree | Pass | Wrote the expected `src/placeholders_config.json`; unsupported config input exited `1` and wrote nothing. |
| Full fixture render compared with pre-change baseline | Pass | All `42` generated files are byte-for-byte identical. |
| `venv/bin/pip check` | Pass | No broken requirements found. |
| `venv/bin/python -m build` | Pass | Built `ks_email_parser-1.0.0.tar.gz` and `ks_email_parser-1.0.0-py3-none-any.whl`. |
| `venv/bin/twine check dist/*` | Pass | Both the sdist and wheel metadata passed validation. |
| Extracted-sdist clean install and `CI=1 make test` | Pass | The sdist includes `requirements/requirements.txt`, `tests/fixtures`, `tests/src`, and `tests/templates_html`; the removed root requirements file is absent, all `99` tests passed at `80%` coverage, and `pip check` passed. |
| Exact-minimum `setuptools==82.0.1`, `wheel==0.47.0` no-isolation build | Pass | Built both artifacts and passed Twine metadata checks at the declared backend floor. |
| Fresh wheel install plus focused renderer/Markdown tests | Pass | `38` tests passed from installed package code; `pip check`, import, CLI version, and config-generation smokes passed. |
| Runtime-only wheel plus local `sdiff==2.0.0`/Mistune `3.3.4` co-install | Pass | `pip check` and imports passed; all `42` rendered files matched the baseline byte-for-byte. |
| Wheel/sdist content and metadata inspection | Pass | The sdist has `90` entries including all fixture types; the `18`-file wheel contains only runtime package files/metadata and excludes tests, fixtures, `link_shortener`, and a direct `requests` requirement. |
| Updated dependency import/version smoke | Pass | Imported Beautiful Soup 4.15.0, lxml 6.0.2, parse 1.22.1, coverage 7.15.2, and `email_parser.Parser`. |
| `venv/bin/pyupgrade --keep-percent-format --py36-plus ... --py311-plus` | Pass | Ladder completed across `email_parser/*.py` and `tests/*.py`. |
| `venv/bin/pip list --format=freeze` | Pass | No installed `msgpack` distribution; latest selected dependency set installed. |
| `venv/bin/pip install cssutils==2.13.0`, `2.14.0`, `2.15.0` import checks | Fail | Later cssutils releases install but fail `import cssutils` because no importable `encutils` module is present. |
| `ruby -e "require 'yaml'; YAML.load_file('.circleci/config.yml'); puts 'ok'"` | Pass | CircleCI config parses as YAML locally. |
| Travis YAML parse and command assertions | Pass | Config selects Jammy/Python 3.11.9, installs with `make ci-dev-install`, then runs `make lint` and `make test`. |
| `circleci config validate .circleci/config.yml` | Pass | CircleCI CLI reported the config file is valid after moving sample-style reuse into valid `executors` and `commands` sections. |
| `circleci config validate --next .circleci/config.yml` | Pass | CircleCI CLI reported the config file is valid under the next schema. |
| `circleci config process .circleci/config.yml` | Pass | Expanded configuration was written to `/tmp/ks-email-parser-circleci-processed.yml`. |
| `make focal-fossa-local` in `ansible/builder` | Pass | Rebuilt amd64 and arm64 Python 3.11.13 builder images with the `ks-email-parser` wheel-only exception. |
| `make focal-fossa-packages-local DIST_PATH=/tmp/packages SRC_PATH=<target-worktree>` | Pass | Built both architecture dependency sets. x86_64 and aarch64 each produced 15 wheels plus an architecture-specific hashed requirements file; `lxml==6.0.2` was repaired to the corresponding manylinux wheel. |
| `bash builder/audit_pypicloud.sh` | Pass | Audited 16 unique wheel filenames; both current pypicloud nodes reported zero missing wheels. |
| `cmp requirements/requirements.txt /tmp/packages/20.04/requirements.txt` | Pass | The repository lock is byte-for-byte identical to the final pypicloud-only builder output. |
| Deployment-lock policy assertions | Pass | Exactly one `--require-hashes`, one internal `--index-url`, no `--extra-index-url`, no public index, and no VCS reference. |
| focal-fossa amd64 deployment-lock install, `pip check`, import/version smoke | Pass | Installed exclusively from pypicloud and resolved the seven direct runtime pins exactly, including `lxml==6.0.2`. |
| focal-fossa arm64 deployment-lock install, `pip check`, import/version smoke | Pass | Installed exclusively from pypicloud and resolved the same direct runtime pins with the aarch64 lxml wheel. |
| Initial deployment-lock source smoke | Fail (corrected) | The dependency-only lock installed and passed `pip check`, but `import email_parser` failed because the project source was not on `sys.path`; rerunning with the mounted source on `PYTHONPATH` passed on both architectures. |
| `bash -n builder/packager.sh builder/audit_pypicloud.sh` | Pass | Both Ansible builder scripts remain syntactically valid after the scoped package/IP edits. |
| `shellcheck builder/packager.sh builder/audit_pypicloud.sh` | Fail (pre-existing) | Reports existing quoting, array, `cd`, status, and `exit -1` findings outside the scoped package/IP edits. The migration does not broaden into a legacy builder cleanup. |

`make test` still prints legacy fixture warnings for intentionally malformed XML fallback cases; those warnings are covered by
existing tests and do not fail the suite.

## 1.0.1 Release Addendum

Date: 2026-08-28.

The `1.0.1` tag resolves to commit `52ac4a9e7eee94cb857cb9822b15690ac74ea7f7`. This patch release preserves
legacy Markdown strong-delimiter behavior and strips raw or percent-encoded bidirectional marks only when they wrap
rendered link targets. Focused Markdown-extension and renderer regressions cover those changes.

The published `ks_email_parser-1.0.1-py3-none-any.whl` has SHA-256
`e58950c1e92f7314946dd8e54f6087e125367a05522e7cec736dccd3e66ec981`. Email-service PR #439 declares that release,
records the same hash in its combined deployment lock, and passes local `pip check`, unit, integration, and Python
3.6/Python 3.11 compatibility proof with it installed. Fresh remote CI remains a gate after that reviewed diff is pushed.

## Email-service downstream correction

Date: 2026-08-04, updated 2026-08-28.

The final email-service resolver proof confirms that `libks==1.0.12` requires
`lxml==6.0.2`. The previous ks-email-parser pin, `lxml==6.1.1`, made the two
packages impossible to resolve in one environment. The selected `lxml==6.0.2`
pin remains Python 3.11-compatible and is validated by the reader, XML fallback,
rendering, CLI, and golden fixture tests.
