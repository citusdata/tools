# needed variables will be passed in via top-level Makefile

INSTALL := install -c
INSTALL_DATA := $(INSTALL) -m 644
INSTALL_SCRIPT := $(INSTALL) -m 755

POD2MAN := pod2man --center "Citus Data Tools" -r "Citus Data"
MANPAGES := citus_package.1

all: man

man: $(MANPAGES)

%.1: %
	$(POD2MAN) --quotes=none --section 1 $< $@

clean:
	rm -f *.1

installdirs:
	$(INSTALL) -d $(DESTDIR)$(bindir) $(DESTDIR)$(pkgsysconfdir) $(DESTDIR)$(mandir)/man1

install: all installdirs
	$(INSTALL_SCRIPT) citus_package $(DESTDIR)$(bindir)
	$(INSTALL_DATA) $(MANPAGES) $(DESTDIR)$(mandir)/man1

.PHONY: all man clean installdirs install
