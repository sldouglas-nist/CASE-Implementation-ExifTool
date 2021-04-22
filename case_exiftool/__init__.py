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

"""
This tool parses the RDF output of ExifTool, mapping it into UCO properties and relationships-of-assumption.  An analyst should later annotate the output with their beliefs on its verity.
"""

__version__ = "0.3.0"

import argparse
import contextlib
import logging
import os

import rdflib.plugins.sparql

import case_utils

_logger = logging.getLogger(os.path.basename(__file__))

NS_EXIFTOOL_COMPOSITE = rdflib.Namespace("http://ns.exiftool.ca/Composite/1.0/")
NS_EXIFTOOL_ET = rdflib.Namespace("http://ns.exiftool.ca/1.0/")
NS_EXIFTOOL_EXIFTOOL = rdflib.Namespace("http://ns.exiftool.ca/ExifTool/1.0/")
NS_EXIFTOOL_GPS = rdflib.Namespace("http://ns.exiftool.ca/EXIF/GPS/1.0/")
NS_EXIFTOOL_SYSTEM = rdflib.Namespace("http://ns.exiftool.ca/File/System/1.0/")
NS_EXIFTOOL_FILE = rdflib.Namespace("http://ns.exiftool.ca/File/1.0/")
NS_EXIFTOOL_IFD0 = rdflib.Namespace("http://ns.exiftool.ca/EXIF/IFD0/1.0/")
NS_EXIFTOOL_EXIFIFD = rdflib.Namespace("http://ns.exiftool.ca/EXIF/ExifIFD/1.0/")
NS_EXIFTOOL_NIKON = rdflib.Namespace("http://ns.exiftool.ca/MakerNotes/Nikon/1.0/")
NS_EXIFTOOL_PREVIEWIFD = rdflib.Namespace("http://ns.exiftool.ca/MakerNotes/PreviewIFD/1.0/")
NS_EXIFTOOL_INTEROPIFD = rdflib.Namespace("http://ns.exiftool.ca/EXIF/InteropIFD/1.0/")
NS_EXIFTOOL_IFD1 = rdflib.Namespace("http://ns.exiftool.ca/EXIF/IFD1/1.0/")
NS_RDF = rdflib.RDF
NS_RDFS = rdflib.RDFS
NS_UCO_CORE = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/core#")
NS_UCO_LOCATION = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/location#")
NS_UCO_OBSERVABLE = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/observable#")
NS_UCO_TYPES = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/types#")
NS_UCO_VOCABULARY = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/vocabulary#")
NS_XSD = rdflib.namespace.XSD

argument_parser = argparse.ArgumentParser(epilog=__doc__)
argument_parser.add_argument("--base-prefix", default="http://example.org/kb/")
argument_parser.add_argument("--debug", action="store_true")
argument_parser.add_argument("--output-format", help="Override extension-based format guesser.")
argument_parser.add_argument("--print-conv-xml", help="A file recording the output of ExifTool run against some file.  Expects exiftool was run as for --raw-xml, but also with the flag --printConv (note the double-dash).")
argument_parser.add_argument("--raw-xml", help="A file recording the output of ExifTool run against some file.  Expects exiftool was run with -binary, -duplicates, and -xmlFormat.", required=True)
argument_parser.add_argument("out_graph", help="A self-contained RDF graph file, in the format either requested by --output-format or guessed based on extension.")

def controlled_dictionary_object_to_node(graph, controlled_dict):
    n_controlled_dictionary = rdflib.BNode()
    graph.add((
      n_controlled_dictionary,
      NS_RDF.type,
      NS_UCO_TYPES.ControlledDictionary
    ))
    for key in sorted(controlled_dict.keys()):
        v_value = controlled_dict[key]
        try:
            assert isinstance(v_value, rdflib.Literal)
        except:
            _logger.info("v_value = %r." % v_value)
            raise
        n_entry = rdflib.BNode()
        graph.add((
          n_controlled_dictionary,
          NS_UCO_TYPES.entry,
          n_entry
        ))
        graph.add((
          n_entry,
          NS_RDF.type,
          NS_UCO_TYPES.ControlledDictionaryEntry
        ))
        graph.add((
          n_entry,
          NS_UCO_TYPES.key,
          rdflib.Literal(key)
        ))
        graph.add((
          n_entry,
          NS_UCO_TYPES.value,
          v_value
        ))
    return n_controlled_dictionary

class ExifToolRDFMapper(object):
    """
    This class maps ExifTool RDF predicates into UCO objects and Facets.

    The implementation strategy is:
    * Iterating through an if-elif ladder of IRIs with known interpretation strategies; and
    * Lazily instantiating objects with class @property methods.
    The lazy (or just-in-time) instantiation is because some graph objects can be needed for various reasons, but because of ExifTool's varied format coverage, it would not be appropriate to create each object each time.  For instance, on encountering GPS data in a JPEG's EXIF data (prefixes "http://ns.exiftool.ca/Composite/1.0/GPS", "http://ns.exiftool.ca/EXIF/GPS/1.0/GPS"), three things need to be created:
    * A Location object.
    * A derivation and assumption relationship between the original trace and the inferred Location object.
    * Entries in the EXIF dictionary.
    Separately, other EXIF properties like picture dimension descriptors need the EXIF dictionary.  The first IRI found to need the dictionary will trigger its creation, leading to its serialization.

    Those interested in extending this tool's mapping coverage of ExifTool IRIs are encouraged to update the method map_raw_and_printconv_iri.
    """

    def __init__(self, graph, ns_base):
        assert isinstance(graph, rdflib.Graph)

        # TODO Build n_file_facet and n_content_data_facet from new case_file function, or inherit from graph that is just that file.
        self._exif_dictionary_dict = None
        self._graph = graph
        self._kv_dict_raw = None
        self._kv_dict_printconv = None
        self._mime_type = None
        self._n_camera_object = None
        self._n_camera_object_device_facet = None
        self._n_content_data_facet = None
        self._n_exif_dictionary_object = None
        self._n_exif_facet = None
        self._n_file_facet = None
        self._n_location_object = None
        self._n_location_object_latlong_facet = None
        self._n_observable_object = None
        self._n_raster_picture_facet = None
        self._n_relationship_object_location = None
        self._oo_slug = None
        self.ns_base = ns_base

    def map_raw_and_printconv_iri(self, exiftool_iri):
        """
        This method implements mapping into UCO for known ExifTool IRIs.

        This method has a side effect of mutating the internal variables:
        * self._kv_dict_raw
        * self._kv_dict_raw
        * self._exiftool_predicate_iris
        """
        assert isinstance(exiftool_iri, str)
        #_logger.debug("map_raw_and_printconv_iri(%r)." % exiftool_iri)

        if exiftool_iri == "http://ns.exiftool.ca/EXIF/IFD0/1.0/Make":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.graph.add((
              self.n_camera_object_device_facet,
              NS_UCO_OBSERVABLE.manufacturer,
              v_printconv
            ))
        elif exiftool_iri == "http://ns.exiftool.ca/EXIF/IFD0/1.0/Model":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.graph.add((
              self.n_camera_object_device_facet,
              NS_UCO_OBSERVABLE.model,
              v_raw
            ))
        elif exiftool_iri == "http://ns.exiftool.ca/File/1.0/MIMEType":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.mime_type = v_raw.toPython()
            # Special case - graph logic is delayed for this IRI, because of needing to initialize the base ObservableObject based on the value.
        elif exiftool_iri == "http://ns.exiftool.ca/File/System/1.0/FileSize":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.graph.add((
              self.n_content_data_facet,
              NS_UCO_OBSERVABLE.sizeInBytes,
              rdflib.Literal(v_raw.toPython(), datatype=NS_XSD.long)
            ))
        elif exiftool_iri == "http://ns.exiftool.ca/Composite/1.0/GPSAltitude":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            l_altitude = rdflib.Literal(v_raw.toPython(), datatype=NS_XSD.decimal)
            self.graph.add((
              self.n_location_object_latlong_facet,
              NS_UCO_LOCATION.altitude,
              l_altitude
            ))
        elif exiftool_iri == "http://ns.exiftool.ca/Composite/1.0/GPSLatitude":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            l_latitude = rdflib.Literal(v_raw.toPython(), datatype=NS_XSD.decimal)
            self.graph.add((
              self.n_location_object_latlong_facet,
              NS_UCO_LOCATION.latitude,
              l_latitude
            ))
        elif exiftool_iri == "http://ns.exiftool.ca/Composite/1.0/GPSLongitude":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            l_longitude = rdflib.Literal(v_raw.toPython(), datatype=NS_XSD.decimal)
            self.graph.add((
              self.n_location_object_latlong_facet,
              NS_UCO_LOCATION.longitude,
              l_longitude
            ))
        elif exiftool_iri == "http://ns.exiftool.ca/Composite/1.0/GPSPosition":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.graph.add((
              self.n_location_object,
              NS_RDFS.label,
              v_printconv
            ))
        elif exiftool_iri in {
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSAltitudeRef",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSAltitude",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLatitudeRef",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLatitude",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLongitudeRef",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLongitude"
        }:
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            dict_key = exiftool_iri.replace("http://ns.exiftool.ca/EXIF/GPS/1.0/GPS", "")
            self.exif_dictionary_dict[dict_key] = v_raw
        elif exiftool_iri == "http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageHeight":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.exif_dictionary_dict["Image Height"] = v_raw
            if not self._n_raster_picture_facet is None:
                self.graph.add((
                  self.n_raster_picture_facet,
                  NS_UCO_OBSERVABLE.pictureHeight,
                  rdflib.Literal(int(v_raw.toPython()))
                ))
        elif exiftool_iri == "http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageWidth":
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            self.exif_dictionary_dict["Image Width"] = v_raw
            if not self._n_raster_picture_facet is None:
                self.graph.add((
                  self.n_raster_picture_facet,
                  NS_UCO_OBSERVABLE.pictureWidth,
                  rdflib.Literal(int(v_raw.toPython()))
                ))
        else:
            # Somewhat in the name of information preservation, somewhat as a progress marker on converting data: Attach all remaining unconverted properties directly to the ObservableObject.  Provide both values to assist with mapping decisions.
            (v_raw, v_printconv) = self.pop_iri(exiftool_iri)
            if not v_raw is None:
                self.graph.add((
                  self.n_observable_object,
                  rdflib.URIRef(exiftool_iri),
                  v_raw
                ))
            if not v_printconv is None:
                self.graph.add((
                  self.n_observable_object,
                  rdflib.URIRef(exiftool_iri),
                  v_printconv
                ))

    def map_raw_and_printconv_rdf(self, filepath_raw_xml, filepath_printconv_xml):
        """
        Loads the print-conv and raw graphs into a dictionary for processing by consuming known IRIs.

        This function has a side effect of mutating the internal variables:
        * self._kv_dict_raw
        * self._kv_dict_raw
        * self._exiftool_predicate_iris
        """
        # Output key: Graph predicate from file RDF-corrected IRI.
        # Output value: Object (whether Literal or URIRef).
        def _xml_file_to_dict(xml_file):
            kv_dict = dict()
            with contextlib.closing(rdflib.Graph()) as in_graph:
                in_graph.parse(xml_file, format="xml")
                query = rdflib.plugins.sparql.prepareQuery("""\
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
}""")
                for (result_no, result) in enumerate(in_graph.query(query)):
                    # v_object might be a literal, might be an object reference.  "v" for "varying".  Because some properties are binary, do not decode v_object.
                    (
                      n_subject,
                      p_predicate,
                      v_object,
                    ) = result
                    subject_iri = n_subject.toPython()
                    predicate_iri = p_predicate.toPython()
                    kv_dict[predicate_iri] = v_object
            return kv_dict
        self._kv_dict_raw = _xml_file_to_dict(filepath_raw_xml)
        self._kv_dict_printconv = _xml_file_to_dict(filepath_printconv_xml)
        self._exiftool_predicate_iris = set(self._kv_dict_raw.keys()) | set(self._kv_dict_printconv.keys())

        # Start by mapping some IRIs that affect the base observable object.
        self.map_raw_and_printconv_iri("http://ns.exiftool.ca/File/1.0/MIMEType")

        # Determine slug by MIME type.
        self.oo_slug = "file-"  # The prefix "oo_" means generic observable object.
        if self.mime_type == "image/jpeg":
            self.oo_slug = "picture-"
        else:
            _logger.warning("TODO - MIME type %r not yet implemented." % mime_type)

        # Access observable object to instantiate it with the oo_slug value.
        _ = self.n_observable_object

        # Finish special case MIME type processing left undone by map_raw_and_printconv_iri.
        if not self.mime_type is None:
            self.graph.add((
              self.n_content_data_facet,
              NS_UCO_OBSERVABLE.mimeType,
              rdflib.Literal(self.mime_type)
            ))
        # Define the raster picture facet depending on MIME type.
        mime_type_to_picture_type = {
          "image/jpeg": "jpg"
        }
        if self.mime_type in mime_type_to_picture_type:
            l_picture_type = rdflib.Literal(mime_type_to_picture_type[self.mime_type])
            self.graph.add((
              self.n_raster_picture_facet,
              NS_UCO_OBSERVABLE.pictureType,
              l_picture_type
            ))

        # Create independent sorted copy of IRI set, because this iteration loop will mutate the set.
        sorted_exiftool_predicate_iris = sorted(self._exiftool_predicate_iris)
        for exiftool_predicate_iri in sorted_exiftool_predicate_iris:
            self.map_raw_and_printconv_iri(exiftool_predicate_iri)

        # Derive remaining objects.
        if not self._exif_dictionary_dict is None:
            _ = self.n_exif_dictionary_object
        if not self._n_location_object is None:
            _ = self.n_relationship_object_location

    def pop_iri(self, exiftool_iri):
        """
        Returns: (raw_object, printconv_object) from input graphs.

        This function has a side effect of mutating the internal variables:
        * self._kv_dict_raw
        * self._kv_dict_raw
        * self._exiftool_predicate_iris
        The exiftool_iri is removed from each of these dicts and set.
        """
        assert isinstance(exiftool_iri, str)
        v_raw = None
        v_printconv = None
        if exiftool_iri in self._exiftool_predicate_iris:
            self._exiftool_predicate_iris -= {exiftool_iri}
        if exiftool_iri in self._kv_dict_raw:
            v_raw = self._kv_dict_raw.pop(exiftool_iri)
        if exiftool_iri in self._kv_dict_printconv:
            v_printconv = self._kv_dict_printconv.pop(exiftool_iri)
        return (v_raw, v_printconv)

    @property
    def exif_dictionary_dict(self):
        """
        Initialized on first access.
        """
        if self._exif_dictionary_dict is None:
            self._exif_dictionary_dict = dict()
        return self._exif_dictionary_dict

    @property
    def graph(self):
        """
        No setter provided.
        """
        return self._graph

    @property
    def mime_type(self):
        return self._mime_type

    @mime_type.setter
    def mime_type(self, value):
        assert isinstance(value, str)
        self._mime_type = value
        return self._mime_type

    @property
    def n_camera_object(self):
        """
        Initialized on first access.
        """
        if self._n_camera_object is None:
            self._n_camera_object = rdflib.URIRef(self.ns_base["device-" + case_utils.local_uuid.local_uuid()])
            self.graph.add((
              self._n_camera_object,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.ObservableObject
            ))
        return self._n_camera_object

    @property
    def n_camera_object_device_facet(self):
        """
        Initialized on first access.
        """
        if self._n_camera_object_device_facet is None:
            self._n_camera_object_device_facet = rdflib.BNode()
            self.graph.add((
              self._n_camera_object_device_facet,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.DeviceFacet
            ))
            self.graph.add((
              self.n_camera_object,
              NS_UCO_CORE.hasFacet,
              self._n_camera_object_device_facet
            ))
        return self._n_camera_object_device_facet

    @property
    def n_content_data_facet(self):
        """
        Initialized on first access.
        """
        if self._n_content_data_facet is None:
            self._n_content_data_facet = rdflib.BNode()
            self.graph.add((
              self._n_content_data_facet,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.ContentDataFacet
            ))
            self.graph.add((
              self.n_observable_object,
              NS_UCO_CORE.hasFacet,
              self._n_content_data_facet
            ))
        return self._n_content_data_facet

    @property
    def n_exif_dictionary_object(self):
        """
        Initialized on first access.
        """
        if self._n_exif_dictionary_object is None:
            self._n_exif_dictionary_object = controlled_dictionary_object_to_node(self.graph, self.exif_dictionary_dict)
            self.graph.add((
              self.n_exif_facet,
              NS_UCO_OBSERVABLE.exifData,
              self._n_exif_dictionary_object
            ))
        return self._n_exif_dictionary_object

    @property
    def n_exif_facet(self):
        """
        Initialized on first access.
        """
        if self._n_exif_facet is None:
            self._n_exif_facet = rdflib.BNode()
            self.graph.add((
              self._n_exif_facet,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.EXIFFacet
            ))
            self.graph.add((
              self.n_observable_object,
              NS_UCO_CORE.hasFacet,
              self._n_exif_facet
            ))
        return self._n_exif_facet

    @property
    def n_file_facet(self):
        """
        Initialized on first access.
        """
        if self._n_file_facet is None:
            self._n_file_facet = rdflib.BNode()
            self.graph.add((
              self._n_file_facet,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.File
            ))
            self.graph.add((
              self.n_observable_object,
              NS_UCO_CORE.hasFacet,
              self._n_file_facet
            ))
        return self._n_file_facet

    @property
    def n_location_object(self):
        """
        Initialized on first access.
        """
        if self._n_location_object is None:
            self._n_location_object = rdflib.URIRef(self.ns_base["location-" + case_utils.local_uuid.local_uuid()])
            self.graph.add((
              self._n_location_object,
              NS_RDF.type,
              NS_UCO_LOCATION.Location
            ))
        return self._n_location_object

    @property
    def n_location_object_latlong_facet(self):
        """
        Initialized on first access.
        """
        if self._n_location_object_latlong_facet is None:
            self._n_location_object_latlong_facet = rdflib.BNode()
            self.graph.add((
              self._n_location_object_latlong_facet,
              NS_RDF.type,
              NS_UCO_LOCATION.LatLongCoordinates
            ))
            self.graph.add((
              self.n_location_object,
              NS_UCO_CORE.hasFacet,
              self._n_location_object_latlong_facet
            ))
        return self._n_location_object_latlong_facet

    @property
    def n_observable_object(self):
        """
        Initialized on first access.
        """
        if self._n_observable_object is None:
            self._n_observable_object = rdflib.URIRef(self.ns_base[self.oo_slug + case_utils.local_uuid.local_uuid()])
            # TODO Prepare list of more interesting types on adoption of the UCO release providing the ObservableObject subclass hierarchy.
            self.graph.add((
              self._n_observable_object,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.ObservableObject
            ))
        return self._n_observable_object

    @property
    def n_raster_picture_facet(self):
        """
        Initialized on first access.
        """
        if self._n_raster_picture_facet is None:
            self._n_raster_picture_facet = rdflib.BNode()
            self.graph.add((
              self._n_raster_picture_facet,
              NS_RDF.type,
              NS_UCO_OBSERVABLE.RasterPictureFacet
            ))
            self.graph.add((
              self.n_observable_object,
              NS_UCO_CORE.hasFacet,
              self._n_raster_picture_facet
            ))
        return self._n_raster_picture_facet

    @property
    def n_relationship_object_location(self):
        """
        Initialized on first access.
        """
        if self._n_relationship_object_location is None:
            self._n_relationship_object_location = rdflib.URIRef(self.ns_base["relationship-" + case_utils.local_uuid.local_uuid()])
            self.graph.add((
              self._n_relationship_object_location,
              NS_RDF.type,
              NS_UCO_CORE.Relationship
            ))
            self.graph.add((
              self._n_relationship_object_location,
              NS_UCO_CORE.source,
              self.n_location_object
            ))
            self.graph.add((
              self._n_relationship_object_location,
              NS_UCO_CORE.target,
              self.n_observable_object
            ))
            self.graph.add((
              self._n_relationship_object_location,
              NS_UCO_CORE.kindOfRelationship,
              rdflib.Literal("Extracted_From", datatype=NS_UCO_VOCABULARY.ObservableObjectRelationshipVocab)
            ))
        return self._n_relationship_object_location

    @property
    def ns_base(self):
        return self._ns_base

    @ns_base.setter
    def ns_base(self, value):
        assert isinstance(value, rdflib.Namespace)
        self._ns_base = value
        return self._ns_base

    @property
    def oo_slug(self):
        return self._oo_slug

    @oo_slug.setter
    def oo_slug(self, value):
        assert isinstance(value, str)
        self._oo_slug = value
        return self._oo_slug

def main():
    case_utils.local_uuid.configure()

    args = argument_parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    NS_BASE = rdflib.Namespace(args.base_prefix)
    out_graph = rdflib.Graph()

    out_graph.namespace_manager.bind("exiftool-Composite", NS_EXIFTOOL_COMPOSITE)
    out_graph.namespace_manager.bind("exiftool-et", NS_EXIFTOOL_ET)
    out_graph.namespace_manager.bind("exiftool-ExifTool", NS_EXIFTOOL_EXIFTOOL)
    out_graph.namespace_manager.bind("exiftool-System", NS_EXIFTOOL_SYSTEM)
    out_graph.namespace_manager.bind("exiftool-File", NS_EXIFTOOL_FILE)
    out_graph.namespace_manager.bind("exiftool-GPS", NS_EXIFTOOL_GPS)
    out_graph.namespace_manager.bind("exiftool-IFD0", NS_EXIFTOOL_IFD0)
    out_graph.namespace_manager.bind("exiftool-ExifIFD", NS_EXIFTOOL_EXIFIFD)
    out_graph.namespace_manager.bind("exiftool-Nikon", NS_EXIFTOOL_NIKON)
    out_graph.namespace_manager.bind("exiftool-PreviewIFD", NS_EXIFTOOL_PREVIEWIFD)
    out_graph.namespace_manager.bind("exiftool-InteropIFD", NS_EXIFTOOL_INTEROPIFD)
    out_graph.namespace_manager.bind("exiftool-IFD1", NS_EXIFTOOL_IFD1)
    out_graph.namespace_manager.bind("kb", NS_BASE)
    out_graph.namespace_manager.bind("uco-core", NS_UCO_CORE)
    out_graph.namespace_manager.bind("uco-location", NS_UCO_LOCATION)
    out_graph.namespace_manager.bind("uco-observable", NS_UCO_OBSERVABLE)
    out_graph.namespace_manager.bind("uco-types", NS_UCO_TYPES)
    out_graph.namespace_manager.bind("uco-vocabulary", NS_UCO_VOCABULARY)

    exiftool_rdf_mapper = ExifToolRDFMapper(out_graph, NS_BASE)
    exiftool_rdf_mapper.map_raw_and_printconv_rdf(args.raw_xml, args.print_conv_xml)

    #_logger.debug("args.output_format = %r." % args.output_format)
    output_format = args.output_format or case_utils.guess_format(args.out_graph)

    out_graph.serialize(destination=args.out_graph, format=output_format)

if __name__ == "__main__":
    main()
