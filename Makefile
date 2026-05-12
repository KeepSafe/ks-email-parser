PYTHON=venv/bin/python
PIP=venv/bin/pip
NOSE=venv/bin/pynose
FLAKE=venv/bin/flake8
EMAILS_TEMPLATES_URI=git@github.com:KeepSafe/emails.git
EMAILS_PATH=emails
GUI_BIN=ks-email-parser
FLAGS=--with-coverage --cover-inclusive --cover-erase --cover-package=email_parser --cover-min-percentage=70
PYPICLOUD_HOST=pypicloud.getkeepsafe.local
TWINE=./venv/bin/twine


env:
	test -d venv || python3.11 -m venv venv
	$(PIP) install --upgrade pip
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

lint: flake

test: lint
	$(NOSE) -s $(FLAGS)

vtest:
	$(NOSE) -s -v $(FLAGS)

testloop:
	while sleep 1; do $(NOSE) -s $(FLAGS); done

cov cover coverage:
	$(NOSE) -s --with-cover --cover-html --cover-html-dir ./coverage $(FLAGS)
	echo "open file://`pwd`/coverage/index.html"

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


.PHONY: env dev install publish rungui flake lint test vtest testloop cov cover coverage clean
