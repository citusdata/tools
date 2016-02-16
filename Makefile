PACKAGE_NAME := citustools

# logic from http://stackoverflow.com/a/11206700
SUBDIRS := $(addsuffix /., uncrustify)
TARGETS := all clean install
SUBDIRS_TARGETS := $(foreach t,$(TARGETS),$(addsuffix $t,$(SUBDIRS)))

.PHONY : $(TARGETS) $(SUBDIRS_TARGETS)

$(TARGETS) : % : $(addsuffix %,$(SUBDIRS))

$(SUBDIRS_TARGETS) :
	$(MAKE) -C $(@D) $(@F:.%=%)
