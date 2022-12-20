#!/usr/bin/make -f

# This software was developed at the National Institute of Standards
# and Technology by employees of the Federal Government in the course
# of their official duties. Pursuant to title 17 Section 105 of the
# United States Code this software is not subject to copyright
# protection and is in the public domain. NIST assumes no
# responsibility whatsoever for its use by other parties, and makes
# no guarantees, expressed or implied, about its quality,
# reliability, or any other characteristic.
#
# We would appreciate acknowledgement if the software is used.

SHELL := /bin/bash

PYTHON3 ?= $(shell which python3.8 2>/dev/null || which python3.7 2>/dev/null || which python3.6 2>/dev/null || which python3)
ifeq ($(PYTHON3),)
$(error python3 not found)
endif

# This recipe intentionally blank.
all:

.PHONY: \
  download

.git_submodule_init.done.log: \
  .gitmodules
	# Log current submodule pointers.
	cd dependencies \
	  && git diff . \
	    | cat
	git submodule update --init
	$(MAKE) \
	  --directory dependencies/CASE-Examples-QC \
	  .git_submodule_init.done.log
	touch $@

check: \
  dependencies/CASE-Examples-QC/tests/ontology_vocabulary.txt
	$(MAKE) \
	  --directory tests \
	  check

clean:
	@rm -rf \
	  *.egg-info \
	  build \
	  dist
	@$(MAKE) \
	  --directory tests \
	  clean
	@#A full clean here erases test files and causes unnecessary rebuilding for the purposes of testing ExifTool mapping.
	@rm -f \
	  dependencies/CASE-Examples-QC/.lib.done.log

dependencies/CASE-Examples-QC/tests/ontology_vocabulary.txt: \
  .git_submodule_init.done.log
	$(MAKE) \
	  PYTHON3=$(PYTHON3) \
	  --directory dependencies/CASE-Examples-QC \
	  .venv.done.log
	$(MAKE) \
	  PYTHON3=$(PYTHON3) \
	  --directory dependencies/CASE-Examples-QC/tests \
	  ontology_vocabulary.txt
	test -r $@

distclean: \
  clean
	@rm -f \
	  .git_submodule_init.done.log \
	  dependencies/CASE-Examples-QC/.lib.done.log \
	  dependencies/CASE-Examples-QC/lib/rdf-toolkit.jar
	@$(MAKE) \
	  --directory tests \
	  distclean

download: \
  dependencies/CASE-Examples-QC/tests/ontology_vocabulary.txt
	$(MAKE) \
	  --directory tests \
	  download
