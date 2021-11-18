# needed variables will be passed in via top-level Makefile

INSTALL := install -c
INSTALL_SCRIPT := $(INSTALL) -m 755
ENTERPRISE_MERGE_SCRIPTS := $(filter-out README.md Makefile,$(wildcard *))

all:

clean:

install: all
	$(INSTALL_SCRIPT) $(ENTERPRISE_MERGE_SCRIPTS) $(DESTDIR)$(bindir)

.PHONY: clean installdirs install
