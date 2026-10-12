PYTHON=venv/bin/python
PIP=venv/bin/pip
NOSE=venv/bin/pynose
FLAKE=venv/bin/flake8
EMAILS_TEMPLATES_URI=git@github.com:KeepSafe/emails.git
EMAILS_PATH=emails
GUI_BIN=ks-email-parser
PYNOSE_SHARED_FLAGS=-s --with-coverage --cover-inclusive --cover-erase --cover-package=email_parser --cover-min-percentage=70 tests
PYNOSE_FLAGS=$(PYNOSE_SHARED_FLAGS)
PYPICLOUD_HOST=pypicloud.getkeepsafe.local
TWINE=./venv/bin/twine

ifdef CI
PYNOSE_FLAGS += --cover-xml --cover-xml-file=build/coverage/coverage.xml --with-xunit --xunit-file=build/test/results.xml
endif


env:
	test -d venv || python3.11 -m venv venv
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .

dev: env
	$(PIP) install -e ".[tests,devtools]"

install: env

publish:
	rm -rf dist
	$(PYTHON) -m build .
	$(TWINE) upload --verbose --sign --username developer --repository-url http://$(PYPICLOUD_HOST)/simple/ dist/*.whl


rungui:
	test -e $(EMAILS_PATH) && echo Emails templates already cloned || git clone $(EMAILS_TEMPLATES_URI) $(EMAILS_PATH);
	$(GUI_BIN) -s $(EMAILS_PATH)/src -d $(EMAILS_PATH)/target -t $(EMAILS_PATH)/templates_html gui

flake:
	$(FLAKE) email_parser tests

build-dir:
	mkdir -p build/test build/coverage

check-msgpack:
	@echo "Checking for direct msgpack imports..."
	@command -v grep >/dev/null 2>&1 || (echo "ERROR: msgpack import scan failed because grep is unavailable." && exit 1)
	@! grep -rn --include="*.py" -E "^(import msgpack|from msgpack)" email_parser tests \
		|| (echo "ERROR: Direct msgpack import found. Use libks.cfg.*_compat functions instead." && exit 1)

lint: build-dir flake check-msgpack

test-only: build-dir
	$(NOSE) $(PYNOSE_FLAGS)

test: lint test-only

vtest:
	$(NOSE) -v $(PYNOSE_FLAGS)

vtests: vtest

testloop:
	while sleep 1; do $(NOSE) $(PYNOSE_FLAGS); done

cov cover coverage:
	$(NOSE) --with-cover --cover-html --cover-html-dir ./coverage $(PYNOSE_FLAGS)
	echo "open file://`pwd`/coverage/index.html"

ci-env:
	test -d venv || python3.11 -m venv venv
	$(PIP) install --upgrade pip setuptools wheel

ci-dev-install: ci-env
	$(PIP) install -e ".[tests,devtools]"

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
	rm -rf dist
	rm -rf *.egg-info
	rm -rf venv


.PHONY: env dev install publish rungui flake build-dir check-msgpack lint test-only test vtest vtests testloop cov cover coverage ci-env ci-dev-install clean
