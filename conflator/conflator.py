#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023,  2024 Humanitarian OpenStreetMap Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
    
import argparse
import logging
import sys
import os
from sys import argv
from osm_fieldwork.osmfile import OsmFile
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, Polygon, mapping
import shapely
from shapely import wkt
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
from osm_fieldwork.convert import escape
from osm_fieldwork.parsers import ODKParsers
from osm_rawdata.postgres import PostgresClient, uriParser
from geosupport import GeoSupport
# from conflator.geosupport import GeoSupport
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep
from haversine import haversine, Unit
from thefuzz import fuzz, process
from pathlib import Path
from osm_fieldwork.parsers import ODKParsers
from pathlib import Path
from spellchecker import SpellChecker
# from deepdiff import DeepDiff

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']


# A function that returns the 'year' value:
def distSort(data: list):
    """
    Args:
        data (list): The data to sort
    """
    return data['dist']

class Conflator(object):
    def __init__(self,
                 uri: str,
                 boundary: str = None,
                 ):
        """
        Initialize Input data source

        Args:
            source (str): The source URI or file
            uri (str): URI for the primary database
            boundary: str = None

        Returns:
            (Conflator): An instance of this object
        """
        self.postgres = list()
        self.tags = dict()
        self.boundary = None
        # Distance in meters for conflating with postgis
        self.tolerance = 7
        self.data = dict()
        self.analyze = ("building", "name", "amenity", "landuse", "cuisine", "tourism", "leisure")
        # uri = uriParser(source[3:])
        # self.source = "underpass" is not support yet
        # Each thread needs it's own connection to postgres to avoid problems.
        for thread in range(0, cores + 1):
            db = GeoSupport(uri)
            self.postgres.append(db)
            if boundary:
                self.boundary = boundary
                db.clipDB(boundary)

        # log.info("Opening data file: %s" % source)
        # toplevel = Path(source)
        # if toplevel.suffix == ".geosjon":
        #     src = open(source, "r")
        #     self.data = geojson.load(src)
        # elif toplevel.suffix == ".osm":
        #     src = open(source, "r")
        #     osmin = OsmFile()
        #     self.data = osmin.loadFile(source) # input file
        #     if boundary:
        #         gs = GeoSupport(source)
        #         # self.data = gs.clipFile(self.data)

    def makeNewFeature(self,
                       attrs: dict = None,
                       tags: dict = None,
                       ) -> dict:
        """
        Create a new feature with optional data

        Args:
            attrs (dict): All of the attributes and their values
            tags (dict): All of the tags and their values

        Returns:
            (dict): A template feature with no data
        """
        newf = dict()
        if attrs:
            newf['attrs'] = attrs
        else:
            newf['attrs'] = dict()
        if tags:
            newf['tags'] = tags
        else:
            newf['tags'] = dict()
        return newf

    def checkTags(self,
                  feature: Feature,
                  osm: dict,
                  ):
        """
        Check tags between 2 features.

        Args:
            feature (Feature): The feature from the external dataset
            osm (dict): The result of the SQL query

        Returns:
            (int): The number of tag matches
            (dict): The updated tags
        """
        tags = osm['tags']
        hits = 0
        match_threshold = 80
        if osm['tags']['dist'] > float(self.tolerance):
            return 0, osm['tags']
        for key, value in feature['tags'].items():
            if key in tags:
                ratio = fuzz.ratio(value, tags[key])
                if ratio > match_threshold:
                    hits += 1
                else:
                    if key != 'note':
                        tags[f'old_{key}'] = value
            tags[key] = value

        return hits, tags

    def conflateFiles(self,
                    odkspec: str,
                    osmspec: str,
                    threshold: int = 10,
                    ):
        """
        Open the two source files and contlate them.

        Args:
            odkspec (dict): The features from ODK to conflate
            osmspec (dict): The existing OSM data
            threshold (int): Threshold for distance calculations

        Returns:
            (dict):  The conflated output
        """
        odkdata = list()
        osmdata = list()

        # The collected data from ODK
        odkpath = Path(odkspec)
        if odkpath.suffix == '.geojson':
            log.debug(f"Parsing GeoJson files {odkspec}")
            odkfile = open(odkspec, 'r')
            features = geojson.load(odkfile)
            odkdata = features['feature']
        elif odkpath.suffix == '.osm':
            log.debug(f"Parsing OSM XML files {odkspec}")
            osmfile = OsmFile()
            odkdata = osmfile.loadFile(odkspec)
        elif odkpath.suffix == ".csv":
            log.debug(f"Parsing csv files {odkspec}")
            odk = ODKParsers()
            for entry in odk.CSVparser(odkspec):
                odkdata.append(odk.createEntry(entry))
        elif odkpath.suffix == ".json":
            log.debug(f"Parsing json files {odkspec}")
            odk = ODKParsers()
            for entry in odk.JSONparser(odkspec):
                odkdata.append(odk.createEntry(entry))

        # The data extract from OSM
        osmpath = Path(osmspec)
        if osmpath.suffix == '.geojson':
            osmfile = open(osmspec, 'r')
            features = geojson.load(osmfile)
            osmdata = features['features']
        if osmpath.suffix == '.osm':
            osmfile = OsmFile()
            osmdata = osmfile.loadFile(osmspec)

        return self.conflateFeatures(odkdata, osmdata, threshold)

    def conflateFeatures(self,
                    odkdata: list,
                    osmdata: list,
                    threshold: int = 1,
                    spellcheck: bool = True,
                    ):
        """
        Conflate features from ODK against all the features in OSM.

        Args:
            odkdata (list): The features from ODK to conflate
            osmdata (list): The existing OSM data
            threshold (int): Threshold for distance calculations
            spellcheck (bool): Whether to also spell check string values

        Returns:
            (list):  The conflated output
        """
        timer = Timer(text="conflateFeatures() took {seconds:.0f}s")
        timer.start()

        # ODK data is always a single node when mapping buildings, but the
        # OSM data will be a mix of nodes and ways. For the OSM data, the
        # building centroid is used.

        # Most smartphone GPS are 5-10m off most of the time, plus sometimes
        # we're standing in front of an amenity and recording that location
        # instead of in the building.
        # gps_accuracy = 10
        # this is the treshold for fuzzy string matching
        match_threshold = 80
        data = list()
        # New features not in OSM always use negative IDs
        odkid = -100
        osmid = 0
        nodes = dict()
        version = 0
        for entry in odkdata:
            confidence = 0
            maybe = list()
            odktags = dict()
            osmtags = dict()
            feature = dict()
            newtags = dict()
            geom = None
            if 'attrs' in entry:
                # The source came from an OSM XML file
                geom = Point((float(entry["attrs"]["lon"]), float(entry["attrs"]["lat"])))
                odktags = entry['tags']
            elif 'coordinates' in entry:
                # The source came from a GeoJson file
                gps = entry['coordinates']
                geom = Point(float(gps[0]), float(gps[1]))
                odktags = entry['properties']
            wkt = shape(geom)
            for existing in osmdata:
                # We could probably do this using GeoPandas or gdal, but that's
                # going to do the same brute force thing anyway.
                if 'geometry' in existing:
                    geom = existing['geometry']
                osmwkt = shape(geom)
                if osmwkt.geom_type != 'Point':
                    center = shapely.centroid(osmwkt)
                else:
                    center = shape(osmwkt)
                # dist = shapely.hausdorff_distance(center, wkt)
                dist = wkt.distance(center)
                if dist < threshold:
                    # cache all OSM features within our threshold distance
                    # These are needed by ODK, but duplicates of other fields,
                    # so they aren't needed and just add more clutter.
                    maybe.append({"dist": dist, "odk": entry, "osm": existing})

            # Compare tags for everything that got cached
            hits = 0
            if len(maybe) > 0:
                # cache the refs to use in the OSM XML output file
                refs = list()
                odk = dict()
                osm = dict()
                # After sorting, the first entry is the closet feature
                maybe.sort(key=distSort)
                # make consistent data structures from different input formats
                if 'properties' in maybe[0]["odk"]:
                    odk['tags'] = maybe[0]["odk"]['properties']
                    gps = maybe[0]['geometry']
                    odk['attrs']= {'id': odkid, 'lat': gps[0], 'lon': gps[1]}
                    odkversion = odk['properties']['version']
                    if 'title' in odk:
                        del odk['title']
                    if 'label' in odk:
                        del odk['label']
                elif 'attrs' in maybe[0]["odk"]:
                    odk['tags'] = maybe[0]["odk"]['tags']
                    odk['attrs'] = maybe[0]["odk"]['attrs']

                if 'properties' in maybe[0]["osm"]:
                    osm['tags'] = maybe[0]["osm"]['properties']
                    if 'title' in osm['tags']:
                        del osm['tags']['title']
                    if 'label' in osm['tags']:
                        del osm['tags']['label']
                    gps = maybe[0]['osm']['geometry']['coordinates']
                    osm['attrs']= {'id': osm['tags']['id'], 'lat': gps[0], 'lon': gps[1]}
                elif 'attrs' in maybe[0]["osm"]:
                    osm['tags'] = maybe[0]["osm"]['tags']
                    osm['attrs'] = maybe[0]["osm"]['attrs']
                    version = int(osm['attrs']['version']) + 1
                    if 'refs' in maybe[0]['osm']:
                        refs = eval(maybe[0]['osm']['refs'])
                    nodes[osm['attrs']['id']] = osm

                for key, value in odk['tags'].items():
                    # log.debug(f"Comparing: {value} == {value}")
                    if key[:4] == "name":
                        if 'tags' not in osm:
                            breakpoint()
                        # log.debug(f"Comparing: {value} == {osm['tags'][key]}")
                        if key in osm['tags']:
                            if key not in osm['tags']:
                                continue
                            result = fuzz.ratio(value, osm['tags'][key])
                            if result > match_threshold:
                                log.debug(f"Matched: {result}: {key} = {value}")

                                log.debug(f"Got a dup in file!!! {odktags}")
                                hits += 1
                                confidence = result
                                # FIXME: if 100%, perfect match, less than
                                # that probably contains a spelling mistake.
                    else:
                        if odk['tags'] == osm['tags']:
                            # this would be an exact match in tags between odk and osm.
                            # unlikely though.
                            hits += 1
                        else:
                            # diff = DeepDiff(osm['tags'], odk['tags'])
                            # see if the ODK key exists in the OSM tags
                            if key in osm['tags']:
                                hits += 1

            if hits > 0:
                # log.debug(f"HITS: {hits}")
                # If there have been hits, it's probably a duplicate
                attrs = {"id": osm['attrs']["id"], "version": version, 'lat': osm['attrs']['lat'], 'lon': osm['attrs']['lon']}
                newtags = odktags | osmtags
                # These are added by ODK Collect, and not relevant for OSM
                # del newtags['id']
                if "refs" in newtags:
                    del newtags['refs']
                # if "properties" in existing:
                #     attrs["id"] = existing["properties"]["id"]
                # else:
                #     attrs["id"] = existing["attrs"]["id"]
                newtags['fixme'] = "Probably a duplicate!"
                newtags['confidence'] = hits
                if len(refs) == 0:
                    feature = {"attrs": attrs, "version": version, "tags": newtags}
                else:
                    feature = {"attrs": attrs, "version": version, "refs": refs, "tags": newtags}
                # data.append(feature)

            # If no hits, it's new data. ODK data is always just a POI for now
            feature["attrs"] = {"id": odkid, "lat": entry["attrs"]["lat"], "lon": entry["attrs"]["lon"], "version": version, "timestamp": entry["attrs"]["timestamp"]}
            feature["tags"] = odktags
            # print(f"{odkid}: {odktags}")
            odkid -= 1
            data.append(feature)

        timer.stop()
        return data

    def cleanFeature(self,
                     feature: dict,
                     ):
        """
        Remove tags that are attributes instead
        Args:
            feature (dict): The feature to clean

        Returns:
            (dict):  The modified feature
        """
            # We only use the version and ID in the attributes
        if 'id' in feature['tags']:
            del feature['tags']['id']
        if 'version' in feature['tags']:
            del feature['tags']['version']
        if 'title' in feature['tags']:
            del feature['tags']['title']
        if 'label' in feature['tags']:
            del feature['tags']['label']
        return feature

    def dump(self):
        """Dump internal data"""
        print(f"Data source is: {self.source}")
        print(f"There are {len(self.data)} existing features")
        # if len(self.versions) > 0:
        #     for k, v in self.original.items():
        #         print(f"{k}(v{self.versions[k]}) = {v}")

    def conflateData(self,
                     source: str,
                     ) -> dict:
        """
        Conflate all the data. This the primary interfacte for conflation.

        Args:
            source (str): The source file to conflate

        Returns:
            (dict):  The conflated features
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()

        log.info("Opening data file: %s" % source)
        toplevel = Path(source)
        if toplevel.suffix == ".geosjon":
            src = open(source, "r")
            self.data = geojson.load(src)
        elif toplevel.suffix == ".osm":
            src = open(source, "r")
            osmin = OsmFile()
            self.data = osmin.loadFile(source) # input file
            if self.boundary:
                gs = GeoSupport(source)
                # self.data = gs.clipFile(self.data)

        # Use fuzzy string matching to handle minor issues in the name column,
        # which is often used to match an amenity.
        if len(self.data) == 0:
            self.postgres[0].query("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")
        # log.debug(f"OdkMerge::conflateData() called! {len(odkdata)} features")

        # A chunk is a group of threads
        chunk = round(len(self.data) / cores)

        # cycle = range(0, len(odkdata), chunk)

        # Chop the data into a subset for each thread
        newdata = list()
        future = None
        result = None
        index = 0
        if True:                # DEBUGGING HACK ALERT!
            result = conflateThread(self.data, self, index)
            return dict()

        with concurrent.futures.ThreadPoolExecutor(max_workers=cores) as executor:
            i = 0
            subset = dict()
            futures = list()
            for key, value in self.data.items():
                subset[key] = value
                if i == chunk:
                    i = 0
                    result = executor.submit(conflateThread, subset, self, index)
                    index += 1
                    # result.add_done_callback(callback)
                    futures.append(result)
                    subset = dict()
                i += 1
            for future in concurrent.futures.as_completed(futures):
            # # for future in concurrent.futures.wait(futures, return_when='ALL_COMPLETED'):
                log.debug(f"Waiting for thread to complete..")
                # print(f"YYEESS!! {future.result(timeout=10)}")
                newdata.append(future.result(timeout=5))
        timer.stop()
        return newdata
        # return alldata

    def writeOSM(self,
                 data: dict,
                 filespec: str,
                 ):
        osm = OsmFile(filespec)
        for entry in data:
            out = str()
            if 'refs' in entry:
                if len(entry['refs']) > 0:
                    out = osm.createWay(entry, True)
            else:
                out = osm.createNode(entry, True)
            if len(out) > 0:
                osm.write(out)

    def writeGeoJson(self,
                 data: dict,
                 filespec: str,
                 ):
        for entry in data:
            pass

def conflateThread(features: dict,
                   source: str,
                   dbindex: int,
                   ):
    """
    Conflate a subset of the data

    Args:
        feature (dict): The feature to conflate
        source (str): The data source for conflation, file or database
        dbindex (int): An index into the array of postgres connections
    Returns:
        (list): the conflated data output
    """
    timer = Timer(text="conflateThread() took {seconds:.0f}s")
    timer.start()
    log.debug(f"conflateThread() called! {len(features)} features")
    merged = list()
    result = dict()
    dups = 0
    # This is brute force, slow but accurate. Process each feature
    # and look for a possible match with existing data.
    for key, value in features.items():
        id = int(value['attrs']['id'])
        # Each of the conflation methods take a single feature
        # as a parameter, and returns a possible match or a zero
        # length dictionary.
        if id > 0:
            # Any feature ID greater than zero is existing data.
            if source.source[:3] != "PG:":
                result = source.conflateFile(value)
            else:
                # Any feature ID less than zero is new data collected
                # using geopoint in the XLSForm.
                result = source.conflateById(value, dbindex)
        elif id < 0:
            result = source.conflateNode(value, dbindex)
            if len(result) == 0:
                result = source.conflateWay(value, dbindex)
        if result and len(result) > 0:
            # Merge the tags and attributes together, the OSM data and ODK data.
            # If no match is found, the ODK data is used to create a new feature.
            if 'fixme' in result['tags']:
                dups += 1
                # newf = source.cleanFeature(result)
                attrs = value['attrs'] | result['attrs']
                tags = value['tags'] | result['tags']
                merged.append({'attrs': attrs, 'tags': tags})
            else:
                merged.append(value)
        else:
            merged.append(value)
            # log.error(f"There are no results!")
    timer.stop()
    log.debug(f"Found {dups} duplicates")
    return merged


def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program conflates external data with existing features in OSM.",
        epilog="""
    This program conflates external datasets with OSM data. It can use a postgres
database, or a GeoJson and OSM XML files as the input sources.

        Examples:
                To conflate two files
         ./conflator.py -v -s camping-2024_06_14.osm -e extract.geojson

                To conflate a file using postgres
         ./conflator.py -v -s camping-2024_06_14.geojson -u localhost/usa -b utah.geojson
        
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-u", "--uri", help="OSM Database URI")
    parser.add_argument("-e", "--extract", help="The OSM data extract")
    parser.add_argument("-s", "--source", required=True, help="The ODK data to conflate")
    parser.add_argument("-t", "--threshold", default=1, help="Threshold for distance calculations")
    parser.add_argument("-o", "--outfile", help="Output file from the conflation")
    parser.add_argument("-b", "--boundary", help="Optional boundary polygon to limit the data size")

    args = parser.parse_args()
    indata = None
    source = None

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(threadName)10s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)

    if not args.extract and not args.uri:
        parser.print_help()
        log.error("You must supply a database URI or a data extract file!")
        quit()

    outfile = None
    if args.outfile:
        outfile = args.outfile
    else:
        toplevel = Path(args.source)

    conflate = Conflator(args.uri)

    if args.extract is not None and len(args.extract) > 0:
        data = conflate.conflateFiles(args.source, args.extract, int(args.threshold))

    jsonout = f"{toplevel.stem}-out.geojson"
    osmout = f"{toplevel.stem}-out.osm"

    conflate.writeOSM(data, osmout)
    conflate.writeGeoJson(data, jsonout)

    log.info(f"Wrote {osmout}")
    log.info(f"Wrote {jsonout}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
