export prefix := /usr/local
export bindir := $(prefix)/bin
JQ_LIBDIR := $(abspath $(addsuffix ../lib/jq,$(dir $(shell which jq))))

INSTALL := install -c
INSTALL_DATA := $(INSTALL) -m 644
INSTALL_SCRIPT := $(INSTALL) -m 755

DASHBOARD_SCRIPTS := $(filter-out pkg.jq schema.ddl Makefile,$(wildcard *))

all:

installdirs:
	$(INSTALL) -d $(DESTDIR)$(bindir) $(JQ_LIBDIR)

install: all installdirs
	$(INSTALL_SCRIPT) $(DASHBOARD_SCRIPTS) $(DESTDIR)$(bindir)
	$(INSTALL_DATA) pkg.jq $(JQ_LIBDIR)

.PHONY: clean installdirs install
