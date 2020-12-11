# Test suite

This directory houses proof-of-functionality tests of code developed in this repository.  ExifTool was run to create test data, but is not yet part of the test suite.

The directories are organized by sample data source.

* [`govdocs1/`](govdocs1/) - Convert ExifTool output from analyzing samples from the govdocs1 corpus.


## Running the test suite

Run `make check`.  `make check` should be run from one directory up, at least once, to trigger some downloads.
