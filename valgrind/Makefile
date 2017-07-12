# needed variables will be passed in via top-level Makefile

INSTALL := install -c
INSTALL_SCRIPT := $(INSTALL) -m 755
VALGRIND_SCRIPTS := $(filter-out README.md Makefile,$(wildcard *))

all:

clean:
	rm -f $(VALGRIND_SCRIPTS)

install: all
	$(INSTALL_SCRIPT) $(VALGRIND_SCRIPTS) $(DESTDIR)$(bindir)

.PHONY: clean installdirs install
