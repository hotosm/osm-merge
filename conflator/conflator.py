#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024 Humanitarian OpenStreetMap Team
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
from shapely.geometry import shape, LineString, Polygon, mapping
import shapely
from shapely.ops import transform
from shapely import wkt
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
from osm_fieldwork.convert import escape
from osm_fieldwork.parsers import ODKParsers
# from osm_merge.geosupport import GeoSupport
from geosupport import GeoSupport
import pyproj
import asyncio
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
from osm_rawdata.pgasync import PostgresClient
from tqdm import tqdm
import tqdm.asyncio
import xmltodict
# from deepdiff import DeepDiff
import math

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
# Try doubling the number of cores, since the CPU load is
# still reasonable.
cores = info['count'] * 2

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# A function that returns the 'year' value:
def distSort(data: list):
    """
    Args:
        data (list): The data to sort
    """
    return data['dist']

async def conflateThread(odkdata: list,
                   osmdata: list,
                   threshold: float = 7.0,
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
    cutils = Conflator()
    # Progress bar
    # xpbar = tqdm.tqdm(odkdata)
    # for entry in pbar:
    for entry in odkdata:
        confidence = 0
        maybe = list()
        odktags = dict()
        osmtags = dict()
        feature = dict()
        newtags = dict()
        geom = None
        # if "attrs" in entry:
        #     odk = cutils.osmToFeature(entry)
        # else:
        #     odk = entry

        for existing in osmdata:
            # We could probably do this using GeoPandas or gdal, but that's
            # going to do the same brute force thing anyway.

            # existing = dict()
            # if "attrs" in osm:
            #     existing = self.osmToFeature(osm)
            # else:
            #     existing = osm

            # If the input file is in OSM XML format, we don't want to
            # conflate the nodes with no tags. They are used to build
            # the geometry for the way, and after that aren't needed anymore.
            # If the node has tags, then it's a POI, which we do conflate.
            if entry["geometry"]["type"] == "Point" and len(entry["properties"]) <= 2:
                continue
            if existing["geometry"]["type"] == "Point" and len(existing["properties"]) <= 2:
                continue

            dist = float()
            try:
                dist = await cutils.getDistance(entry, existing)
            except:
                breakpoint()

            if dist <= threshold:
                log.debug(f"DIST: {dist / 1000}km. {dist}m")
                log.debug(f"ENTRY: {entry["properties"]}")
                log.debug(f"EXISTING: {existing["properties"]}")
                if dist <= 0.0:
                    # Probably an exact hit, likely from data imported
                    # into OSM from the same source.
                    maybe.append({"dist": dist, "odk": entry, "osm": existing})
                    break
                # cache all OSM features within our threshold distance
                # These are needed by ODK, but duplicates of other fields,
                # so they aren't needed and just add more clutter.
                maybe.append({"dist": dist, "odk": entry, "osm": existing})

            # if osmwkt.geom_type != 'Point':
            #     center = shapely.centroid(osmwkt)
            # else:
            #     center = shape(osmwkt)
            # # dist = shapely.hausdorff_distance(center, wkt)
            # dist = wkt.distance(center)
            # if dist < threshold:
            #     # cache all OSM features within our threshold distance
            #     # These are needed by ODK, but duplicates of other fields,
            #     # so they aren't needed and just add more clutter.
            #     maybe.append({"dist": dist, "odk": entry, "osm": existing})

        # Compare tags for everything that got cached
        hits = 0
        if len(maybe) > 0:
            # cache the refs to use in the OSM XML output file
            refs = list()
            odk = dict()
            osm = dict()
            # After sorting, the first entry is the closet feature
            maybe.sort(key=distSort)
            if 'title' in odk:
                del odk['title']
            if 'label' in odk:
                del odk['label']

            hits, tags = await cutils.checkTags(maybe, existing)
            log.debug(f"TAGS: {tags}")
            breakpoint()
            # if hits > 0:
            #     # log.debug(f"HITS: {hits}")
            #     # If there have been hits, it's probably a duplicate
            #     attrs = {"id": osm['attrs']["id"], "version": version, 'lat': osm['attrs']['lat'], 'lon': osm['attrs']['lon']}
            #     newtags = odktags | osmtags
            #     # These are added by ODK Collect, and not relevant for OSM
            #     # del newtags['id']
            #     if "refs" in newtags:
            #         del newtags['refs']
            #     # if "properties" in existing:
            #     #     attrs["id"] = existing["properties"]["id"]
            #     # else:
            #     #     attrs["id"] = existing["attrs"]["id"]
            #     newtags['fixme'] = "Probably a duplicate!"
            #     newtags['confidence'] = hits
            #     if len(refs) == 0:
            #         feature = {"attrs": attrs, "version": version, "tags": newtags}
            #     else:
            #         feature = {"attrs": attrs, "version": version, "refs": refs, "tags": newtags}
            #     # data.append(feature)

            # # If no hits, it's new data. ODK data is always just a POI for now
            # feature["attrs"] = {"id": odkid, "lat": entry["attrs"]["lat"], "lon": entry["attrs"]["lon"], "version": version, "timestamp": entry["attrs"]["timestamp"]}
            # feature["tags"] = odktags
            # # print(f"{odkid}: {odktags}")
            # odkid -= 1
            # data.append(feature)

    timer.stop()
    return data

class Conflator(object):
    def __init__(self,
                 uri: str = None,
                 boundary: str = None
                 ):
        """
        Initialize Input data sources.

        Args:
            uri (str): URI for the primary database
            boundary (str, optional): Boundary to limit SQL queries

        Returns:
            (Conflator): An instance of this object
        """
        self.postgres = list()
        self.tags = dict()
        self.boundary = boundary
        self.dburi = uri
        self.primary = None
        if boundary:
            infile = open(boundary, 'r')
            self.boundary = geojson.load(infile)
            infile.close()
        # Distance in meters for conflating with postgis
        self.tolerance = 7
        self.data = dict()
        self.analyze = ("building", "name", "amenity", "landuse", "cuisine", "tourism", "leisure")

    async def getDistance(self,
            newdata: Feature,
            olddata: Feature,
            ) -> float:
        """
        Compute the distance between two features in meters

        Args:
            newdata (Feature): A feature from the external dataset
            olddata (Feature): A feature from the existing OSM dataset

        Returns:
            (float): The distance between the two features
        """
        # dist = shapely.hausdorff_distance(center, wkt)
        dist = 0.0

        # Transform so the results are in meters instead of degress of the
        # earth's radius.
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:32633')
            )
        newobj = transform(project.transform, shape(newdata["geometry"]))
        oldobj = transform(project.transform, shape(olddata["geometry"]))

        if oldobj.geom_type == "LineString" and newobj.geom_type == "LineString":
            # Compare two highways
            dist = newobj.distance(oldobj)
        elif oldobj.geom_type == "Point" and newobj.geom_type == "LineString":
            # We only want to compare LineStrings, so force the distance check
            # to be False
            dist = 12345678.9
        elif oldobj.geom_type == "Point" and newobj.geom_type == "Point":
            dist = newobj.distance(oldobj)
        elif oldobj.geom_type == "Polygon" and newobj.geom_type == "Polygon":
            # compare two buildings
            pass
        elif oldobj.geom_type == "Polygon" and newobj.geom_type == "Point":
            # Compare a point with a building, used for ODK Collect data
            center = shapely.centroid(oldobj)
            dist = newdata.distance(center)
        elif oldobj.geom_type == "Point" and newobj.geom_type == "LineString":
            dist = newdata.distance(oldobj)

        return dist # * 111195

    async def checkTags(self,
                        extfeat: Feature,
                        osm: Feature,
                        ):
        """
        Check tags between 2 features.

        Args:
            extfeat (Feature): The feature from the external dataset
            osm (Feature): The result of the SQL query

        Returns:
            (int): The number of tag matches
            (dict): The updated tags
        """
        match_threshold = 80
        hits = 0
        props = dict()
        id = 0
        version = 0
        for key, value in extfeat['properties'].items():
            if key in osm["properties"]:
                if key == "osm_id" or key == "id":
                    # External data not from an OSM source always has
                    # negative IDs to distinguish it from current OSM data.
                    if value <= 0:
                        id = int(osm["properties"][key])
                    else:
                        id = int(value)
                    props["id"] = id
                    continue
                elif key == "version":
                    # Always use the OSM version, since it gets incremented
                    # so JOSM see it's been modified.
                    version = int(osm["properties"][key])
                    props["version"] = version
                    continue
                # Name may also be name:en, name:np, etc... There may also be
                # multiple name:* values in the tags.
                elif key[:4] == "name":
                    # Usually it's the name field that has the most variety in
                    # in trying to match strings. This often is differences in
                    # capitalization, singular vs plural, and typos from using
                    # your phone to enter the name. Course names also change
                    # too so if it isn't a match, use the new name from the
                    # external dataset.
                    ratio = fuzz.ratio(value.lower(), osm["properties"][key].lower())
                    if ratio > match_threshold:
                        hits += 1
                        props["ratio"] = ratio
                        props[key] = value
                        props[f"old_{key}"] = osm["properties"][key]
                    else:
                        if key != 'note':
                            props[key] = value
                else:
                    # All the other keys are usually a defined OSM tag.
                    # Course the new value is probably more up to data
                    # than what is in OSM. Keep both in the properties
                    # for debugging tag conflation.
                    props[key] = value
                    if value != osm["properties"][key]:
                        props[f"old_{key}"] = osm["properties"][key]
                    else:
                        hits += 1

        return hits, props

    def loadFile(
        self,
        osmfile: str,
    ) -> list:
        """
        Read a OSM XML file generated by osm_fieldwork and convert
        it to GeoJson for consistency.

        Args:
            osmfile (str): The OSM XML file to load

        Returns:
            (list): The entries in the OSM XML file
        """
        alldata = list()
        size = os.path.getsize(osmfile)
        with open(osmfile, "r") as file:
            xml = file.read(size)
            doc = xmltodict.parse(xml)
            if "osm" not in doc:
                logging.warning("No data in this instance")
                return False
            data = doc["osm"]
            if "node" not in data:
                logging.warning("No nodes in this instance")
                return False

        nodes = dict()
        for node in data["node"]:
            properties = {
                "id": int(node["@id"]),
            }
            if "@version" not in node:
                properties["version"] = 1
            else:
                properties["version"] = node["@version"]

            if "@timestamp" in node:
                properties["timestamp"] = node["@timestamp"]

            if "tag" in node:
                for tag in node["tag"]:
                    if type(tag) == dict:
                        properties[tag["@k"]] = tag["@v"].strip()
                        # continue
                    else:
                        properties[node["tag"]["@k"]] = node["tag"]["@v"].strip()
                    # continue
            geom = Point((float(node["@lon"]), float(node["@lat"])))
            # cache the nodes so we can dereference the refs into
            # coordinates, but we don't need them in GeoJson format.
            nodes[properties["id"]] = geom
            if len(properties) > 2:
                alldata.append(Feature(geometry=geom, properties=properties))

        for way in data["way"]:
            properties = {
                "id": int(way["@id"]),
            }
            refs = list()
            if len(way["nd"]) > 0:
                for ref in way["nd"]:
                    refs.append(int(ref["@ref"]))
            properties["refs"] = refs

            if "@version" not in node:
                properties["version"] = 1
            else:
                properties["version"] = node["@version"]

            if "@timestamp" in node:
                attrs["timestamp"] = node["@timestamp"]

            if "tag" in way:
                for tag in way["tag"]:
                    if type(tag) == dict:
                        properties[tag["@k"]] = tag["@v"].strip()
                        # continue
                    else:
                        properties[way["tag"]["@k"]] = way["tag"]["@v"].strip()
                    # continue
            # geom =
            tmp = list()
            for ref in refs:
                tmp.append(nodes[ref]['coordinates'])
            geom = LineString(tmp)
            alldata.append(Feature(geometry=geom, properties=properties))

        return alldata

    async def initInputDB(self,
                        config: str = None,
                        dburi: str = None,
                        ) -> bool:
        """
        When async, we can't initialize the async database connection,
        so it has to be done as an extrat step.

        Args:
            dburi (str, optional): The database URI
            config (str, optional): The config file from the osm-rawdata project
        Returns:
            (bool): Whether it initialiized
        """
        db = GeoSupport(dburi, config)
        await db.initialize()
        self.postgres.append(db)

        return True

    async def initOutputDB(self,
                        dburi: str = None,
                        ):
        """
        When async, we can't initialize the async database connection,
        so it has to be done as an extrat step.

        Args:
            dburi (str, optional): The database URI
            config (str, optional): The config file from the osm-rawdata project
        """
        if dburi:
            self.dburi = dburi
            await self.createDBThreads(dburi, config)
        elif self.dburi:
            await self.createDBThreads(self.dburi, config)

    async def createDBThreads(self,
                        uri: str = None,
                        config: str = None,
                        execs: int = cores,
                        ) -> bool:
        """
        Create threads for writting to the primary datatbase to avoid
        problems with corrupting data.

        Args:
            uri (str): URI for the primary database
            config (str, optional): The config file from the osm-rawdata project
            threads (int, optional): The number of threads to create

        Returns:
            (bool): Whether the threads were created sucessfully
        """
        # Each thread needs it's own connection to postgres to avoid problems
        # when inserting or updating the primary database.
        if uri:
            for thread in range(0, execs + 1):
                db = GeoSupport(uri)
                await db.initialize(uri, config)
                if not db:
                    return False
                self.postgres.append(db)
            if self.boundary:
                if 'features' in self.boundary:
                    poly = self.boundary["features"][0]["geometry"]
                else:
                    poly = shape(self.boundary['geometry'])

                # FIXME: we only need to clip once to create the view, this is not
                # confirmed yet.
                await db.clipDB(poly, self.postgres[0])

            return True

    # def makeNewFeature(self,
    #                    attrs: dict = None,
    #                    tags: dict = None,
    #                    ) -> dict:
    #     """
    #     Create a new feature with optional data

    #     Args:
    #         attrs (dict): All of the attributes and their values
    #         tags (dict): All of the tags and their values

    #     Returns:
    #         (dict): A template feature with no data
    #     """
    #     newf = dict()
    #     if attrs:
    #         newf['attrs'] = attrs
    #     else:
    #         newf['attrs'] = dict()
    #     if tags:
    #         newf['tags'] = tags
    #     else:
    #         newf['tags'] = dict()
    #     return newf

    async def conflateData(self,
                    odkspec: str,
                    osmspec: str,
                    threshold: float = 10.0,
                    ) -> list:
        """
        Open the two source files and contlate them.

        Args:
            odkspec (str): The external data uri
            osmspec (str): The existing OSM data uri
            threshold (float): Threshold for distance calculations in meters

        Returns:
            (list):  The conflated output
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        odkdata = list()
        osmdata = list()

        result = list()
        if odkspec[:3].lower() == "pg:":
            db = GeoSupport(odkspec[3:])
            result = await db.queryDB()
        else:
            odkdata = self.parseFile(odkspec)

        if osmspec[:3].lower() == "pg:":
            db = GeoSupport(osmspec[3:])
            result = await db.queryDB()
        else:
            osmdata = self.parseFile(osmspec)

        entries = len(odkdata)
        chunk = round(entries / cores)

        alldata = list()
        tasks = list()

        # log.warning(f"This makes take time, so please wait...")
        async with asyncio.TaskGroup() as tg:
            for block in range(0, entries, chunk):
                log.debug(f"Dispatching thread {block}:{block + chunk}")
                tasks.append(tg.create_task(conflateThread(odkdata[block:block + chunk - 1], osmdata)))
            #for task in tasks:
            #    alldata += task.result()

        timer.stop()

        # return await conflateThread(odkdata, osmdata, threshold)
        return alldata

    def dump(self):
        """Dump internal data"""
        print(f"Data source is: {self.dburi}")
        print(f"There are {len(self.data)} existing features")
        # if len(self.versions) > 0:
        #     for k, v in self.original.items():
        #         print(f"{k}(v{self.versions[k]}) = {v}")

    def parseFile(self,
                filespec: str,
                ) ->list:
        odkpath = Path(filespec)
        odkdata = list()
        if odkpath.suffix == '.geojson':
            # FIXME: This should also work for any GeoJson file, not
            # only ODK ones, but this has yet to be tested.
            log.debug(f"Parsing GeoJson files {odkpath}")
            odkfile = open(odkpath, 'r')
            features = geojson.load(odkfile)
            odkdata = features['features']
        elif odkpath.suffix == '.osm':
            log.debug(f"Parsing OSM XML files {odkpath}")
            osmfile = OsmFile()
            odkdata = self.loadFile(odkpath)
        elif odkpath.suffix == ".csv":
            log.debug(f"Parsing csv files {odkpath}")
            odk = ODKParsers()
            for entry in odk.CSVparser(odkpath):
                odkdata.append(odk.createEntry(entry))
        elif odkpath.suffix == ".json":
            log.debug(f"Parsing json files {odkpath}")
            odk = ODKParsers()
            for entry in odk.JSONparser(odkpath):
                odkdata.append(odk.createEntry(entry))
        return odkdata

    def conflateDB(self,
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

    def osmToFeature(self,
                     osm: dict(),
                     ) -> Feature:
        """
        Convert an entry from an OSM XML file with attrs and tags into
        a GeoJson Feature.

        Args:
            osm (dict): The OSM entry

        Returns:
            (Feature): A GeoJson feature
        """
        if "attrs" not in osm:
            return Feature(geometry=shape(osm["geometry"]), properties=osm["properties"])

        if "osm_id" in osm["attrs"]:
            id = osm["attrs"]["osm_id"]
        else:
            id = osm["attrs"]["id"]
        props = {"id": id,
                }
        if "version" in osm["attrs"]:
            props["version"] = osm["attrs"]["version"]

        props.update(osm["tags"])
        # It's a way, so no coordinate
        if "refs" in osm:
            return Feature(properties=props)
        else:
            geom = Point((float(osm["attrs"]["lon"]), float(osm["attrs"]["lat"])))

            return Feature(geometry=geom, properties=props)

async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program conflates external data with existing features in OSM.",
        epilog="""
This program conflates external datasets with OSM data. It can use a
postgres database, a GeoJson file, or any of all three ODK formats files
as the input sources. Some options are only used for greater control when
using a database. By default this uses the yaml based config files in the
osm-rawdata project, which are also used by the FMTM project. It is possible
to pass a custom SQL query, which if two databases are being conflated,
would apply to either.

        Examples:
                To conflate two files
         ./conflator.py -v -s camping-2024_06_14.osm -e extract.geojson

                To conflate a file using postgres
         ./conflator.py -v -s camping-2024_06_14.geojson -e PG:localhost/usa -b utah.geojson
        
The data extract file must be produced using the pgasync.py script in the
osm-rawdata project on pypi.org or https://github.com/hotosm/osm-rawdata.
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-e", "--extract", help="The base OSM data")
    parser.add_argument("-q", "--query", help="Custom SQL when using a database")
    parser.add_argument("-c", "--config", default="highway", help="The config file for the SQL query")
    parser.add_argument("-s", "--source", required=True, help="The external data to conflate")
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

    if args.query and args.config:
        parser.print_help()
        log.error("You must supply a either a conig file or custom SQL!")
        quit()

    outfile = None
    if args.outfile:
        outfile = args.outfile
    else:
        toplevel = Path(args.source)

    conflate = Conflator(args.extract, args.boundary)
    if args.extract[:3].lower() == "pg:":
        await conflate.initInputDB(args.config, args.extract[3:])

    if args.source[:3].lower() == "pg:":
        await conflate.initInputDB(args.config, args.source[3:])

    data = await conflate.conflateData(args.source, args.extract, float(args.threshold))

    jsonout = f"{toplevel.stem}-out.geojson"
    osmout = f"{toplevel.stem}-out.osm"

    # await conflate.writeOSM(data, osmout)
    # await conflate.writeGeoJson(data, jsonout)

    log.info(f"Wrote {osmout}")
    log.info(f"Wrote {jsonout}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
