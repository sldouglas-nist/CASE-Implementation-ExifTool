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

top_srcdir := $(shell cd .. ; pwd)

PYTHON3 ?= $(shell which python3.8 2>/dev/null || which python3.7 2>/dev/null || which python3.6 2>/dev/null || which python3)
ifeq ($(PYTHON3),)
$(error python3 not found)
endif

all: \
  .venv.done.log
	$(MAKE) \
	  --directory govdocs1

.PHONY: \
  download

.venv.done.log: \
  $(top_srcdir)/.git_submodule_init.done.log \
  $(top_srcdir)/case_exiftool/__init__.py \
  $(top_srcdir)/case_exiftool/local_uuid.py \
  $(top_srcdir)/dependencies/CASE-Utilities-Python/tests/requirements.txt \
  $(top_srcdir)/setup.cfg \
  $(top_srcdir)/setup.py \
  requirements.txt
	rm -rf venv
	$(PYTHON3) -m virtualenv \
	  --python=$(PYTHON3) \
	  venv
	source venv/bin/activate \
	  && pip install \
	    --upgrade \
	    pip \
	    setuptools
	source venv/bin/activate \
	  && cd $(top_srcdir)/dependencies/CASE-Utilities-Python \
	    && pip install \
	      .
	source venv/bin/activate \
	  && pip install \
	    --requirement $(top_srcdir)/dependencies/CASE-Utilities-Python/tests/requirements.txt
	source venv/bin/activate \
	  && cd $(top_srcdir) \
	    && python3 setup.py install
	source venv/bin/activate \
	  && pip install \
	    -r requirements.txt
	touch $@

check: \
  .venv.done.log
	$(MAKE) \
	  --directory govdocs1 \
	  check

clean:
	@rm -f \
	  .venv.done.log
	@rm -rf \
	  .pytest_cache \
	  venv
	@$(MAKE) \
	  --directory govdocs1 \
	  clean

download: \
  .venv.done.log
