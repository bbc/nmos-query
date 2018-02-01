PYTHON=`which python`
DESTDIR=/
PROJECT=ipsregistryquery

TEST_DEPS=\
	mock \
	gevent \
	nose2

VENV=virtpython
VENV_ACTIVATE=$(VENV)/bin/activate
VENV_MODULE_DIR=$(VENV)/lib/python2.7/site-packages
VENV_TEST_DEPS=$(addprefix $(VENV_MODULE_DIR)/,$(TEST_DEPS))

all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system (only during development)"
	@echo "make deb - Generate a deb package - for local testing"
	@echo "make clean - Get rid of scratch and byte files"
	@echo "make test - Run any unit tests"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

deb:
	debuild -uc -us

clean:
	$(PYTHON) setup.py clean
	dh_clean
	rm -rf build/ MANIFEST
	find . -name '*.pyc' -delete
	find . -name '*.py,cover' -delete
	rm -rf $(VENV)

$(VENV):
	virtualenv --system-site-packages $@

$(VENV_TEST_DEPS): $(VENV)
	. $(VENV_ACTIVATE); pip install $(@F)

test: $(VENV_TEST_DEPS)
	. $(VENV_ACTIVATE); nose2 --with-coverage --coverage=nmosquery --coverage-report=annotate --coverage-report=term

.PHONY: test clean deb install source all
