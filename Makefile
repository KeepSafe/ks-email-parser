# Some simple testing tasks (sorry, UNIX only).

PYTHON=venv/bin/python3
PIP=venv/bin/pip
EI=venv/bin/easy_install
NOSE=venv/bin/nosetests
FLAKE=venv/bin/flake8
EMAILS_TEMPLATES_URI=git@github.com:KeepSafe/emails.git
EMAILS_PATH=emails
GUI_BIN=ks-email-parser
FLAGS=--with-coverage --cover-inclusive --cover-erase --cover-package=email_parser --cover-min-percentage=70


update:
	$(PIP) install -U pip
	$(PIP) install -U .

env:
	test -d venv || python3 -m venv venv

dev: env update
	$(PIP) install .[tests,devtools]

install: env update

rungui:
	test -e $(EMAILS_PATH) && echo Emails templates already cloned || git clone $(EMAILS_TEMPLATES_URI) $(EMAILS_PATH);
	$(GUI_BIN) -s $(EMAILS_PATH)/src -d $(EMAILS_PATH)/target -t $(EMAILS_PATH)/templates_html gui

flake:
	$(FLAKE) email_parser tests

test: flake
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
	rm -rf venv


.PHONY: all build env linux run pep test vtest testloop cov clean
