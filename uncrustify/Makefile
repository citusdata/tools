PACKAGE_NAME = citustools

prefix = /usr/local
bindir = $(prefix)/bin
datarootdir = $(prefix)/share
mandir = $(datarootdir)/man
sysconfdir = $(prefix)/etc
pkgsysconfdir = $(sysconfdir)/$(PACKAGE_NAME)

INSTALL = install -c
INSTALL_DATA = $(INSTALL) -m 644
INSTALL_SCRIPT = $(INSTALL) -m 755

POD2MAN=pod2man --center "Citus Data Tools" -r "Citus Data"
MANPAGES = citus_indent.1

all: man

man: $(MANPAGES)

%.1: %
	$(POD2MAN) --quotes=none --section 1 $< $@

clean:
	rm -f *.1

installdirs:
	$(INSTALL) -d $(DESTDIR)$(bindir) $(DESTDIR)$(pkgsysconfdir) $(DESTDIR)$(mandir)/man1

install: all installdirs
	$(INSTALL_SCRIPT) citus_indent $(DESTDIR)$(bindir)
	$(INSTALL_DATA) $(MANPAGES) $(DESTDIR)$(mandir)/man1
	$(INSTALL_DATA) citus-style.cfg $(DESTDIR)$(pkgsysconfdir)
	perl -pi -e 's,/usr/local/etc/citustools,$(pkgsysconfdir),g' \
	$(DESTDIR)$(bindir)/citus_indent \
	$(DESTDIR)$(mandir)/man1/citus_indent.1
