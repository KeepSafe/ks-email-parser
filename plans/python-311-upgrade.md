# Python 3.11.13 + Pyproject + Markdown 3 Upgrade Plan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

PLANS.md is checked into this repo at `PLANS.md` and this document must be maintained in accordance with it.

## Purpose / Big Picture

The goal is to keep ks-email-parser behavior identical while upgrading to Python 3.11.13, moving packaging metadata to `pyproject.toml`, switching the test runner to pynose, and updating dependencies (including lxml v5 and Markdown 3.x). After the change, a developer can install dependencies on Python 3.11.13, run the same CLI, and see the same rendered HTML/text outputs for our custom email syntax. Success is visible by running the test suite and seeing new targeted tests prove the custom markdown and CSS behavior still matches today.

## Progress

- [x] 2026-02-03 00:00Z Plan drafted and ExecPlan scaffolding installed (PLANS.md and AGENTS.md).
- [x] 2026-02-04 00:02Z Added baseline tests for inline text and base URL image behavior in `tests/test_markdown_ext.py`, ran `make test`, and confirmed all tests passed on current dependency versions.
- [x] 2026-02-04 02:41Z Added `pyproject.toml`, simplified `setup.py`, synced `requirements.txt`, bumped `.python-version` and `.travis.yml`, and switched Makefile to pynose with Python 3.11 venv creation.
- [x] 2026-02-04 02:41Z Ported `email_parser/markdown_ext.py` to Markdown 3.x InlineProcessor API; updated renderer for lxml 5 + inlinestyler compatibility; added renderer helper tests; `make test` and `make coverage` pass (93 tests, 85% coverage).
- [x] 2026-02-04 02:41Z `/review` checkpoints executed; no blocking issues found beyond preexisting URL handling edge cases.

## Surprises & Discoveries

- Observation: `make dev` failed under the default Python 3.14 because lxml 4.9.4 cannot build on that runtime.
  Evidence: Build error in lxml C extensions (undeclared _PySet_NextEntry) when using Python 3.14; resolved by creating a Python 3.11 venv before running tests.
- Observation: Upgrading to lxml 5 breaks inlinestyler’s CSSSelector usage and HTML serialization expectations.
  Evidence: `CSSSelector.evaluate` missing in lxml 5; output formatting regressed until renderer switched to lxml parsing and XML serialization with placeholder spacing restoration.
- Observation: URL detection still treats protocol-relative URLs as relative, which appears to be preexisting behavior.
  Evidence: Review noted `//example.com/img` is not matched by the absolute URL regex and would be prefixed if base_url is set.

## Decision Log

- Decision: Keep `setup.cfg` for flake8 and coverage configuration while moving packaging metadata to `pyproject.toml`.
  Rationale: Avoid adding new tooling dependencies purely for configuration migration; the existing configs are stable and can remain.
  Date/Author: 2026-02-03, Codex
- Decision: Use pynose as the test runner while keeping tests in unittest style.
  Rationale: Current tests already use unittest.TestCase and patches, so pynose should run them without structural changes.
  Date/Author: 2026-02-03, Codex
- Decision: Use Python 3.11 for local venv creation during the upgrade work.
  Rationale: lxml 4.9.4 fails to build under Python 3.14 in the current environment, and Python 3.11 is the target runtime.
  Date/Author: 2026-02-04, Codex
- Decision: Add a compatibility shim for `inlinestyler.cssselect.CSSSelector.evaluate` when running on lxml 5.
  Rationale: inlinestyler 0.2.x still calls `.evaluate`, which was removed in lxml 5; mapping to `__call__` preserves behavior without forking dependencies.
  Date/Author: 2026-02-04, Codex
- Decision: Use lxml HTML parsing and XML serialization in `_inline_css`, plus placeholder spacing restoration for `{{ ... }}`.
  Rationale: lxml XML serialization preserves prior whitespace/self-closing formatting and avoids unwanted `%20` encoding in placeholders.
  Date/Author: 2026-02-04, Codex

## Outcomes & Retrospective

Not started.

## Context and Orientation

This repo ships a CLI for rendering email templates with custom Markdown behavior and CSS inlining. Packaging currently lives in `setup.py`, tool config in `setup.cfg`, and runtime pins in `requirements.txt`. Tests live in `tests/` and rely on `unittest`. The custom Markdown behavior is implemented in `email_parser/markdown_ext.py` and consumed by `email_parser/renderer.py` via `markdown.markdown(...)`. The custom behaviors that must not change include:

Inline text blocks: `[[...]]` should render as raw text without paragraph wrapping, used for placing raw values in HTML attributes.

Base URL images: relative image links like `![Alt](/path/img.jpg)` should be rewritten to include `config.base_img_path`.

No-tracking links: links whose href is prefixed with `!` should render with the `!` removed and add `clicktracking="off"`.

Link locale substitution: `{link_locale}` should be replaced with the normalized locale (including mapping rules in config).

CSS inlining: template CSS should be inlined in rendered HTML, relying on `inlinestyler` + `cssutils` + `lxml`.

Markdown 3.x deprecates older `Pattern`/`LinkPattern` APIs, so `email_parser/markdown_ext.py` will need to move to the supported InlineProcessor API to preserve the behaviors above.

## Plan of Work

First, lock in baseline behavior before any dependency upgrades. Add new unit tests that directly exercise the custom Markdown and CSS behaviors above so that test failures clearly indicate behavior drift. These tests should call the existing renderer functions with small inputs so the expected HTML/text output is explicit and readable. Run the current test command to ensure the new tests pass on the existing dependency set.

Next, create `pyproject.toml` with PEP 621 metadata that mirrors `setup.py` and move dependency declarations there. Keep `setup.cfg` for tool configs. Update `.python-version` to 3.11.13 and update CI config to match. Replace pytest references with pynose in the test extras and Makefile. Update dependency pins to Python 3.11 compatible versions, including lxml v5 and Markdown 3.x. Keep `requirements.txt` in sync with `pyproject.toml` runtime pins so installations remain predictable.

Then, refactor `email_parser/markdown_ext.py` to the Markdown 3.x extension API, keeping all custom behaviors identical. This includes replacing `Pattern`, `LinkPattern`, and `ImagePattern` usage with `InlineProcessor` subclasses and updating `extendMarkdown` signatures. The new tests should detect any behavior drift, so update code until tests pass. Ensure the renderer still uses the same Markdown extensions and returns identical HTML/text outputs.

Finally, rerun the full test suite under Python 3.11.13 with upgraded dependencies and record results. Add review checkpoints mid-implementation and before handoff, and update this plan as changes land.

## Concrete Steps

All commands run from the repo root unless noted.

Add baseline tests (before upgrades):

    rg -n "markdown_ext|inline|clicktracking|base_url" tests email_parser
    # Add tests in tests/ (new file ok) to lock in custom Markdown and CSS behaviors.
    make test

Insert `/review` checkpoint after baseline tests:

    codex exec "/review"

Add pyproject, dependency pins, and pynose migration:

    # Create pyproject.toml with packaging metadata and dependencies.
    # Update .python-version and .travis.yml to 3.11.13.
    # Update Makefile and test extras to use pynose.
    # Align requirements.txt with runtime pins.
    make test

Insert `/review` checkpoint after packaging and dependency changes:

    codex exec "/review"

Update Markdown 3.x compatibility:

    # Refactor email_parser/markdown_ext.py to InlineProcessor-based extensions.
    # Run tests until new and existing tests pass.
    make test
    make coverage

Final `/review` checkpoint before handoff:

    codex exec "/review"

## Validation and Acceptance

The change is accepted when all tests pass under Python 3.11.13 with the upgraded dependencies and pynose runner. The newly added tests must verify that inline text `[[...]]`, base URL image rewriting, no-tracking links, locale substitution, and CSS inlining produce the same outputs as before the upgrade. The CLI should still render emails without errors; this can be confirmed by running `ks-email-parser` against `tests/` fixtures and observing that outputs match expected fixtures.

## Idempotence and Recovery

All edits are safe to apply multiple times; re-running `make test` should be repeatable. If a dependency upgrade breaks behavior, revert only that dependency pin to the prior known-good version and rerun the test that failed to isolate the cause. If Markdown 3.x changes are too large to land at once, keep a temporary adapter layer inside `email_parser/markdown_ext.py` that supports both old and new APIs while tests are stabilized, then remove the old path once tests pass.

## Artifacts and Notes

Keep short test output snippets here as evidence during implementation, for example:

    $ make test
    ...
    OK (78 tests)

## Interfaces and Dependencies

The core extension APIs are in `email_parser/markdown_ext.py`. After the upgrade, this module must expose `inline_text()`, `base_url(base_url)`, and `no_tracking()` and they must return Markdown 3.x compatible `Extension` objects using `InlineProcessor` subclasses. The renderer must continue to call `markdown.markdown(text, extensions=extensions)` in `email_parser/renderer.py`.

Dependencies should be pinned to versions that support Python 3.11.13, including lxml v5 and Markdown 3.x. Runtime pins must be declared in `pyproject.toml` and `requirements.txt`, and test/dev pins must include pynose, coverage, and flake8 (or whatever the project already uses). If an updated dependency changes behavior, adjust code to preserve behavior rather than downgrading unless there is a clear compatibility failure.

## Plan Change Notes

Initial plan created to guide the upgrade and testing work.
2026-02-04: Updated Progress, Surprises, and Decision Log after adding baseline tests and encountering Python 3.14/lxml build failures.
2026-02-04: Marked packaging + markdown upgrades complete, recorded inlinestyler/lxml compatibility decisions, and noted passing tests/coverage.
2026-02-04: Recorded /review completion and documented preexisting URL edge-case note.
