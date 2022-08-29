export PACKAGE_NAME = citustools

export prefix := /usr/local
export bindir := $(prefix)/bin
export datarootdir := $(prefix)/share
export mandir := $(datarootdir)/man
export sysconfdir := $(prefix)/etc
export pkgsysconfdir := $(sysconfdir)/$(PACKAGE_NAME)

DIRNAMES = automated_packaging packaging uncrustify valgrind travis

PROPERTY_FILE = toolsvars

COPY_PROPERTY:
	cp -f $(PROPERTY_FILE) $(bindir)

install : COPY_PROPERTY

# logic from http://stackoverflow.com/a/11206700
SUBDIRS := $(addsuffix /., $(DIRNAMES))

TARGETS := all clean install
SUBDIRS_TARGETS := $(foreach t,$(TARGETS),$(addsuffix $t,$(SUBDIRS)))

.PHONY : $(COPY_PROPERTY) $(TARGETS) $(SUBDIRS_TARGETS)

$(TARGETS) : % : $(addsuffix %,$(SUBDIRS))

$(SUBDIRS_TARGETS) :
	$(MAKE) -C $(@D) $(@F:.%=%)

automated_packaging: $(COPY_PROPERTY)
