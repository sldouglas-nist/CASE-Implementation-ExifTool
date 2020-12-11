#!/usr/bin/env python3

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

import setuptools

#TODO - PyPI will need a differently-written README.
with open("README.md", "r") as fh:
    long_description = fh.read()

setup_kwargs = {
  "name": "case_exiftool",
  "version": "attr: case_exiftool.__version__",
  "author": "Alex Nelson",
  "author_email": "alexander.nelson@nist.gov",
  "description": "A mapping of ExifTool to CASE",
  "long_description": long_description,
  "long_description_content_type": "text/markdown",
  "url": "https://github.com/casework/CASE-Implementation-ExifTool",
  "packages": setuptools.find_packages(),
  "classifiers": [
    "Development Status :: 4 - Beta",
    "License :: Public Domain",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3"
  ],
  "python_requires": ">=3.6",
  "install_requires": [
    # TODO This constraint on pyparsing can be removed when rdflib Issue #1190 is resolved.
    # https://github.com/RDFLib/rdflib/issues/1190
    "pyparsing < 3.0.0",
    "python-dateutil",
    "rdflib",
    "requests"
  ],
  "entry_points": {
    "console_scripts": [
      "case_exiftool=case_exiftool:main"
    ]
  }
}

if __name__ == "__main__":
    setuptools.setup(**setup_kwargs)
