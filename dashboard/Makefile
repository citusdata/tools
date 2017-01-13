export prefix := /usr/local
export bindir := $(prefix)/bin
export datarootdir := $(prefix)/share
export mandir := $(datarootdir)/man
export sysconfdir := $(prefix)/etc
export pkgsysconfdir := $(sysconfdir)/$(PACKAGE_NAME)

INSTALL := install -c
INSTALL_SCRIPT := $(INSTALL) -m 755
DASHBOARD_SCRIPTS := $(filter-out Makefile,$(wildcard *))

all:

installdirs:
	$(INSTALL) -d $(DESTDIR)$(bindir)

install: all installdirs
	$(INSTALL_SCRIPT) $(DASHBOARD_SCRIPTS) $(DESTDIR)$(bindir)

.PHONY: clean installdirs install
