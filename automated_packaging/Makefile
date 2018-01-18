# needed variables will be passed in via top-level Makefile

INSTALL := install -c
INSTALL_SCRIPT := $(INSTALL) -m 755
AUTOMATION_SCRIPTS := $(filter-out Makefile,$(wildcard *))

all: 

clean:

install: all
	$(INSTALL_SCRIPT) $(AUTOMATION_SCRIPTS) $(DESTDIR)$(bindir)
	
.PHONY: installdirs install
