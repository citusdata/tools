# needed variables will be passed in via top-level Makefile

INSTALL := install -c
INSTALL_SCRIPT := $(INSTALL) -m 755
TRAVIS_SCRIPTS := $(filter-out README.md Makefile,$(wildcard *))

all:

installdirs:
	$(INSTALL) -d $(DESTDIR)$(bindir)

install: all installdirs
	$(INSTALL_SCRIPT) $(TRAVIS_SCRIPTS) $(DESTDIR)$(bindir)

.PHONY: clean installdirs install
