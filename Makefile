# Some simple testing tasks (sorry, UNIX only).

PYTHON=venv/bin/python
PIP=venv/bin/pip
FLAKE=venv/bin/flake8
FLAGS=


update:
	$(PYTHON) ./setup.py install

install:
	$(PYTHON) ./setup.py install

dev:
	python3 -m venv venv
	./venv/bin/activate
	$(PIP) install flake8 nose coverage
	$(PIP) install -r requirements.txt
	$(PYTHON) ./setup.py develop

flake:
	$(FLAKE) --exclude=./venv ./
