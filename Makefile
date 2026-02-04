# Some simple testing tasks (sorry, UNIX only).

PYTHON=venv/bin/python3
PYTHON_BIN?=python3.11
PIP=venv/bin/pip
EI=venv/bin/easy_install
TEST_RUNNER=venv/bin/nosetests
FLAKE=venv/bin/flake8
EMAILS_TEMPLATES_URI=git@github.com:KeepSafe/emails.git
EMAILS_PATH=emails
GUI_BIN=ks-email-parser
TEST_RUNNER_FLAGS=-s
COVERAGE=venv/bin/coverage
PYPICLOUD_HOST=pypicloud.getkeepsafe.local
TWINE=./venv/bin/twine


update:
	$(PIP) install -U pip
	$(PIP) install -U .

env:
	test -d venv || $(PYTHON_BIN) -m venv venv

dev: env update
	$(PIP) install .[tests,devtools]

install: env update

publish:
	rm -rf dist
	$(PYTHON) -m build .
	$(TWINE) upload --verbose --sign --username developer --repository-url http://$(PYPICLOUD_HOST)/simple/ dist/*.whl


rungui:
	test -e $(EMAILS_PATH) && echo Emails templates already cloned || git clone $(EMAILS_TEMPLATES_URI) $(EMAILS_PATH);
	$(GUI_BIN) -s $(EMAILS_PATH)/src -d $(EMAILS_PATH)/target -t $(EMAILS_PATH)/templates_html gui

flake:
	$(FLAKE) email_parser tests

test: flake
	$(COVERAGE) run $(TEST_RUNNER) $(TEST_RUNNER_FLAGS)

vtest:
	$(COVERAGE) run $(TEST_RUNNER) -v $(TEST_RUNNER_FLAGS)

testloop:
	while sleep 1; do $(TEST_RUNNER) $(TEST_RUNNER_FLAGS); done

cov cover coverage:
	$(COVERAGE) report -m

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -f `find . -type f -name '@*' `
	rm -f `find . -type f -name '#*#' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*.rej' `
	rm -f .coverage
	rm -rf coverage
	rm -rf build
	rm -rf venv


.PHONY: all build env linux run pep test vtest testloop cov clean
