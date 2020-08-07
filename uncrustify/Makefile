# needed variables will be passed in via top-level Makefile

INSTALL := install -c
INSTALL_DATA := $(INSTALL) -m 644
INSTALL_SCRIPT := $(INSTALL) -m 755

POD2MAN := pod2man --center "Citus Data Tools" -r "Citus Data"
MANPAGES := citus_indent.1

all: man

man: $(MANPAGES)

%.1: %
	$(POD2MAN) --quotes=none --section 1 $< $@

clean:
	rm -f *.1

installdirs:
	$(INSTALL) -d $(bindir) $(pkgsysconfdir) $(mandir)/man1

install: all installdirs
	$(INSTALL_SCRIPT) citus_indent $(bindir)
	$(INSTALL_DATA) $(MANPAGES) $(mandir)/man1
	$(INSTALL_DATA) citus-style.cfg $(pkgsysconfdir)
	perl -pi -e 's,/usr/local/etc/citustools,$(pkgsysconfdir),g' \
	$(bindir)/citus_indent \
	$(mandir)/man1/citus_indent.1

.PHONY: all man clean installdirs install
