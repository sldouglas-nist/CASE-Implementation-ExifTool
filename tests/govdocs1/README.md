# govdocs1

Sample data in this directory is based on analysis of files from the govdocs1 corpus, documented here:

[https://digitalcorpora.org/corpora/files](https://digitalcorpora.org/corpora/files)

The directories are named after the identifying number of a file from the corpus.  E.g. `000001.jpg` would have an analysis under `files/000/001`.  Note that because the file extensions are just suggestions from the corpus creators ("not part of the corpus"), they are not included in the directory naming structure here.


## Predicates discovered

A file in this directory lists the ExifTool RDF predicates discovered from analyzing the JPEG files of the govdocs1 corpus.  (These are the files extracted from `files.jpeg.tar`.)  The file was produced by extracting the `.tar` file into a directory, descending into that directory, and running this command:

```bash
exiftool \
  -binary \
  -duplicates
  -recurse \
  -xmlFormat \
  . \
  | sed \
    -e "s_rdf:Description rdf:about='./_rdf:Description rdf:about='http://example.org/kb/govdocs1/_" \
    > ../files.jpeg.xml
```

Then, this SPARQL query run against the 527MB file `files.jpeg.xml` yielded the predicates:

```sparql
SELECT DISTINCT ?p
WHERE {
  ?s ?p ?o .
}
```

The results are [here](predicates_discovered.txt).
