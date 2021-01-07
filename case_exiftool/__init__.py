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

__version__ = "0.1.2"

import argparse
import logging
import os

import rdflib.plugins.sparql

try:
    from case_exiftool import local_uuid
except ImportError:
    if __name__ != "__main__":
        raise
    import local_uuid

_logger = logging.getLogger(os.path.basename(__file__))

NS_EXIFTOOL_COMPOSITE = "http://ns.exiftool.ca/Composite/1.0/"
NS_EXIFTOOL_ET = "http://ns.exiftool.ca/1.0/"
NS_EXIFTOOL_EXIFTOOL = "http://ns.exiftool.ca/ExifTool/1.0/"
NS_EXIFTOOL_GPS = "http://ns.exiftool.ca/EXIF/GPS/1.0/"
NS_EXIFTOOL_SYSTEM = "http://ns.exiftool.ca/File/System/1.0/"
NS_EXIFTOOL_FILE = "http://ns.exiftool.ca/File/1.0/"
NS_EXIFTOOL_IFD0 = "http://ns.exiftool.ca/EXIF/IFD0/1.0/"
NS_EXIFTOOL_EXIFIFD = "http://ns.exiftool.ca/EXIF/ExifIFD/1.0/"
NS_EXIFTOOL_NIKON = "http://ns.exiftool.ca/MakerNotes/Nikon/1.0/"
NS_EXIFTOOL_PREVIEWIFD = "http://ns.exiftool.ca/MakerNotes/PreviewIFD/1.0/"
NS_EXIFTOOL_INTEROPIFD = "http://ns.exiftool.ca/EXIF/InteropIFD/1.0/"
NS_EXIFTOOL_IFD1 = "http://ns.exiftool.ca/EXIF/IFD1/1.0/"
NS_RDF = rdflib.RDF
NS_UCO_CORE = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/core#")
NS_UCO_LOCATION = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/location#")
NS_UCO_OBSERVABLE = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/observable#")
NS_UCO_TYPES = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/types#")
NS_UCO_VOCABULARY = rdflib.Namespace("https://unifiedcyberontology.org/ontology/uco/vocabulary#")
NS_XSD = rdflib.namespace.XSD

argument_parser = argparse.ArgumentParser(epilog=__doc__)
argument_parser.add_argument("--base-prefix", default="http://example.org/kb/")
argument_parser.add_argument("--debug", action="store_true")
argument_parser.add_argument("--output-format", help="RDF syntax to use for out_graph.  Passed to rdflib.Graph.serialize(format=).  The format will be guessed based on the output file extension, but will default to Turtle.")
argument_parser.add_argument("--print-conv-xml", help="A file recording the output of ExifTool run against some file.  Expects exiftool was run as for --raw-xml, but alsow ith the flag --printConv (note the double-dash).")
argument_parser.add_argument("--raw-xml", help="A file recording the output of ExifTool run against some file.  Expects exiftool was run with -binary, -duplicates, and -xmlFormat.", required=True)
argument_parser.add_argument("out_graph", help="A self-contained RDF graph file, in the format requested by --output-format.")

def guess_graph_format(filename):
    ext = os.path.splitext(filename)[-1].replace(".", "")
    if ext in ("json", "json-ld", "jsonld"):
        return "json-ld"
    elif ext in ("ttl", "turtle"):
        return "turtle"
    return "turtle"

def controlled_dictionary_object_to_node(graph, controlled_dict):
    n_controlled_dictionary = rdflib.BNode()
    graph.add((
      n_controlled_dictionary,
      NS_RDF.type,
      NS_UCO_TYPES.ControlledDictionary
    ))
    for key in sorted(controlled_dict.keys()):
        value = controlled_dict[key]
        try:
            assert isinstance(value, rdflib.Literal)
        except:
            _logger.info("value = %r." % value)
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
          value
        ))
    return n_controlled_dictionary

def main():
    local_uuid.configure()

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

    # Load the raw graph into a dictionary for whittle-processing.

    # Key: Graph predicate from file faked IRI.
    # Value: Object (whether literal or IRI).
    kv_dict_raw = dict()
    in_graph_raw = rdflib.Graph()
    in_graph_raw.parse(args.raw_xml, format="xml")
    query = rdflib.plugins.sparql.prepareQuery("""\
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
}""")
    for (result_no, result) in enumerate(in_graph_raw.query(query)):
        # v_object might be a literal, might be an object reference.  "v" for "varying".  Because some properties are binary, do not decode v_object.
        (
          n_subject,
          p_predicate,
          v_object,
        ) = result
        subject_iri = n_subject.toPython()
        predicate_iri = p_predicate.toPython()

        kv_dict_raw[predicate_iri] = v_object
    kv_dict_keys = set(kv_dict_raw.keys())

    # TODO Build these from new case_file function, or inherit from graph that is just that file.
    n_file_facet = rdflib.BNode()
    out_graph.add((
      n_file_facet,
      NS_RDF.type,
      NS_UCO_OBSERVABLE.File
    ))
    n_content_data_facet = rdflib.BNode()
    out_graph.add((
      n_content_data_facet,
      NS_RDF.type,
      NS_UCO_OBSERVABLE.ContentData
    ))

    n_camera = None
    n_exif = None

    mime_type = None
    if "http://ns.exiftool.ca/File/1.0/MIMEType" in kv_dict_keys:
        l_mime_type = kv_dict_raw.pop("http://ns.exiftool.ca/File/1.0/MIMEType")
        mime_type = l_mime_type.toPython()
        out_graph.add((
          n_content_data_facet,
          NS_UCO_OBSERVABLE.mimeType,
          l_mime_type
        ))

    n_raster_picture_facet = None  #TODO Populate.
    oo_slug = "file-"  # The prefix "oo_" means generic observable object.
    oo_types = set()  # Note that before UCO 0.6.0 and the CyberItem subclass hierarchy, this will only get CyberItem.
    # Determine slug and primary type(s) by MIME type.
    if mime_type == "image/jpeg":
        oo_slug = "picture-"
        #TODO This awaits UCO 0.6.0 for a more interesting type.
        oo_types.add(NS_UCO_OBSERVABLE.CyberItem)
    else:
        raise NotImplementedError("TODO - MIME type %r not yet implemented." % mime_type)
    if len(oo_types) == 0:
        oo_types.add(NS_UCO_OBSERVABLE.CyberItem)
    n_oo = rdflib.URIRef(NS_BASE[oo_slug + local_uuid.local_uuid()])
    for oo_type in sorted(oo_types):
        out_graph.add((
          n_oo,
          NS_RDF.type,
          oo_type
        ))
    out_graph.add((
      n_oo,
      NS_UCO_CORE.facets,
      n_content_data_facet
    ))
    out_graph.add((
      n_oo,
      NS_UCO_CORE.facets,
      n_file_facet
    ))

    l_make = kv_dict_raw.get("http://ns.exiftool.ca/EXIF/IFD0/1.0/Make")
    l_model = kv_dict_raw.get("http://ns.exiftool.ca/EXIF/IFD0/1.0/Model")
    if (not l_make is None) or (not l_model is None):
        n_camera = rdflib.URIRef(NS_BASE["device-" + local_uuid.local_uuid()])
        n_device_facet = rdflib.BNode()
        out_graph.add((
          n_camera,
          NS_RDF.type,
          NS_UCO_OBSERVABLE.CyberItem
        ))
        out_graph.add((
          n_device_facet,
          NS_RDF.type,
          NS_UCO_OBSERVABLE.Device
        ))
        out_graph.add((
          n_camera,
          NS_UCO_CORE.facets,
          n_device_facet
        ))
        if not l_make is None:
            out_graph.add((
              n_device_facet,
              NS_UCO_OBSERVABLE.manufacturer,
              l_make
            ))
            if "http://ns.exiftool.ca/EXIF/IFD0/1.0/Make" in kv_dict_raw:
                del kv_dict_raw["http://ns.exiftool.ca/EXIF/IFD0/1.0/Make"]
        if not l_model is None:
            out_graph.add((
              n_device_facet,
              NS_UCO_OBSERVABLE.model,
              l_model
            ))
            if "http://ns.exiftool.ca/EXIF/IFD0/1.0/Model" in kv_dict_raw:
                del kv_dict_raw["http://ns.exiftool.ca/EXIF/IFD0/1.0/Model"]

    # Define the raster picture facet depending on MIME type OR on whether we have a camera object to link.
    mime_type_to_picture_type = {
      "image/jpeg": "jpg"
    }
    if mime_type in mime_type_to_picture_type or not n_camera is None:
        n_raster_picture_facet = rdflib.BNode()
        out_graph.add((
          n_raster_picture_facet,
          NS_RDF.type,
          NS_UCO_OBSERVABLE.RasterPicture
        ))
        out_graph.add((
          n_oo,
          NS_UCO_CORE.facets,
          n_raster_picture_facet
        ))

        # TODO This property has an open question on its usage.
        # https://unifiedcyberontology.atlassian.net/browse/OC-72
        if not n_camera is None:
            out_graph.add((
              n_raster_picture_facet,
              NS_UCO_OBSERVABLE.camera,
              n_camera
            ))

        if mime_type in mime_type_to_picture_type:
            l_picture_type = rdflib.Literal(mime_type_to_picture_type[mime_type])
            out_graph.add((
              n_raster_picture_facet,
              NS_UCO_OBSERVABLE.pictureType,
              l_picture_type
            ))

    l_file_size = kv_dict_raw.get("http://ns.exiftool.ca/File/System/1.0/FileSize")
    if not l_file_size is None:
        out_graph.add((
          n_content_data_facet,
          NS_UCO_OBSERVABLE.sizeInBytes,
          rdflib.Literal(l_file_size.toPython(), datatype=NS_XSD.long)
        ))
        if "http://ns.exiftool.ca/File/System/1.0/FileSize" in kv_dict_raw:
            del kv_dict_raw["http://ns.exiftool.ca/File/System/1.0/FileSize"]

    # On encountering GPS data, three things need to be created:
    # * A Location object.
    # * A derivation and assumption relationship between the original trace and the inferred Location object.
    # * Entries in the EXIF dictionary.

    # Note that this property is not currently consumed by this script.
    if "http://ns.exiftool.ca/Composite/1.0/GPSPosition" in kv_dict_raw:
        del kv_dict_raw["http://ns.exiftool.ca/Composite/1.0/GPSPosition"]

    # Populate exifData dictionary with GPS-namespace values.
    exif_dictionary_object = dict()

    if len({
      "http://ns.exiftool.ca/Composite/1.0/GPSAltitude",
      "http://ns.exiftool.ca/Composite/1.0/GPSLatitude",
      "http://ns.exiftool.ca/Composite/1.0/GPSLongitude",
      "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLatitudeRef",
      "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLatitude",
      "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLongitudeRef",
      "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLongitude"
    } & kv_dict_keys) > 0:
        n_location = rdflib.URIRef(NS_BASE["location-" + local_uuid.local_uuid()])
        n_latlong_facet = rdflib.BNode()
        out_graph.add((
          n_location,
          NS_RDF.type,
          NS_UCO_LOCATION.Location
        ))
        out_graph.add((
          n_latlong_facet,
          NS_RDF.type,
          NS_UCO_LOCATION.LatLongCoordinates
        ))
        out_graph.add((
          n_location,
          NS_UCO_CORE.facets,
          n_latlong_facet
        ))

        # Attach relationship of inference.
        n_relationship = rdflib.URIRef(NS_BASE["relationship-" + local_uuid.local_uuid()])
        out_graph.add((
          n_relationship,
          NS_RDF.type,
          NS_UCO_CORE.Relationship
        ))
        out_graph.add((
          n_relationship,
          NS_UCO_CORE.source,
          n_location
        ))
        out_graph.add((
          n_relationship,
          NS_UCO_CORE.target,
          n_oo
        ))
        out_graph.add((
          n_relationship,
          NS_UCO_CORE.kindOfRelationship,
          rdflib.Literal("Extracted_From", datatype=NS_UCO_VOCABULARY.CyberItemRelationshipVocab)
        ))

        if not kv_dict_raw.get("http://ns.exiftool.ca/Composite/1.0/GPSAltitude") is None:
            v_value = kv_dict_raw.pop("http://ns.exiftool.ca/Composite/1.0/GPSAltitude")
            l_altitude = rdflib.Literal(v_value.toPython(), datatype=NS_XSD.decimal)
            out_graph.add((
              n_latlong_facet,
              NS_UCO_LOCATION.altitude,
              v_value
            ))

        if not kv_dict_raw.get("http://ns.exiftool.ca/Composite/1.0/GPSLatitude") is None:
            v_value = kv_dict_raw.pop("http://ns.exiftool.ca/Composite/1.0/GPSLatitude")
            l_latitude = rdflib.Literal(v_value.toPython(), datatype=NS_XSD.decimal)
            out_graph.add((
              n_latlong_facet,
              NS_UCO_LOCATION.latitude,
              l_latitude
            ))

        if not kv_dict_raw.get("http://ns.exiftool.ca/Composite/1.0/GPSLongitude") is None:
            v_value = kv_dict_raw.pop("http://ns.exiftool.ca/Composite/1.0/GPSLongitude")
            l_longitude = rdflib.Literal(v_value.toPython(), datatype=NS_XSD.decimal)
            out_graph.add((
              n_latlong_facet,
              NS_UCO_LOCATION.longitude,
              l_longitude
            ))

        exif_dict_gps_keys = {
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSAltitudeRef",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSAltitude",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLatitudeRef",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLatitude",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLongitudeRef",
          "http://ns.exiftool.ca/EXIF/GPS/1.0/GPSLongitude"
        }
        for exif_dict_gps_key in exif_dict_gps_keys:
            if not kv_dict_raw.get(exif_dict_gps_key) is None:
                v_value = kv_dict_raw.pop(exif_dict_gps_key)
                dict_key = exif_dict_gps_key.replace("http://ns.exiftool.ca/EXIF/GPS/1.0/GPS", "")
                exif_dictionary_object[dict_key] = v_value

    if len({
      "http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageHeight",
      "http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageWidth"
    }) > 0:
        if not kv_dict_raw.get("http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageHeight") is None:
            v_value = kv_dict_raw.pop("http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageHeight")
            exif_dictionary_object["Image Height"] = v_value
            if not n_raster_picture_facet is None:
                out_graph.add((
                  n_raster_picture_facet,
                  NS_UCO_OBSERVABLE.pictureHeight,
                  rdflib.Literal(int(v_value.toPython()))
                ))
        if not kv_dict_raw.get("http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageWidth") is None:
            v_value = kv_dict_raw.pop("http://ns.exiftool.ca/EXIF/ExifIFD/1.0/ExifImageWidth")
            exif_dictionary_object["Image Width"] = v_value
            if not n_raster_picture_facet is None:
                out_graph.add((
                  n_raster_picture_facet,
                  NS_UCO_OBSERVABLE.pictureWidth,
                  rdflib.Literal(int(v_value.toPython()))
                ))

    if len(exif_dictionary_object) > 0:
        n_exif = rdflib.BNode()
        out_graph.add((
          n_oo,
          NS_UCO_CORE.facets,
          n_exif
        ))
        out_graph.add((
          n_exif,
          NS_RDF.type,
          NS_UCO_OBSERVABLE.EXIF
        ))
        n_exif_dictionary = controlled_dictionary_object_to_node(out_graph, exif_dictionary_object)
        out_graph.add((
          n_exif,
          NS_UCO_OBSERVABLE.exifData,
          n_exif_dictionary
        ))

    # Somewhat in the name of information preservation, somewhat as a progress marker on converting data: Attach all remaining unconverted properties directly to the CyberItem.
    for key in kv_dict_raw.keys():
        out_graph.add((
          n_oo,
          rdflib.URIRef(key),
          kv_dict_raw[key]
        ))

    #_logger.debug("args.output_format = %r." % args.output_format)
    output_format = args.output_format or guess_graph_format(args.out_graph)

    out_graph.serialize(destination=args.out_graph, format=output_format)

if __name__ == "__main__":
    main()
