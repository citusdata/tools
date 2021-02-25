export PACKAGE_NAME = citustools

export prefix := /usr/local
export bindir := $(prefix)/bin
export datarootdir := $(prefix)/share
export mandir := $(datarootdir)/man
export sysconfdir := $(prefix)/etc
export pkgsysconfdir := $(sysconfdir)/$(PACKAGE_NAME)
export TRAVIS=true

DIRNAMES = automated_packaging packaging uncrustify valgrind
ifeq ($(TRAVIS), true)
	DIRNAMES += travis
endif
$(info    TRAVIS is $(TRAVIS))

# logic from http://stackoverflow.com/a/11206700
SUBDIRS := $(addsuffix /., $(DIRNAMES))
TARGETS := all clean install
SUBDIRS_TARGETS := $(foreach t,$(TARGETS),$(addsuffix $t,$(SUBDIRS)))

.PHONY : $(TARGETS) $(SUBDIRS_TARGETS)

$(TARGETS) : % : $(addsuffix %,$(SUBDIRS))

$(SUBDIRS_TARGETS) :
	$(MAKE) -C $(@D) $(@F:.%=%)
