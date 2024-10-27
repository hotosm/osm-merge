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
import re
from sys import argv
from osm_fieldwork.osmfile import OsmFile
from geojson import Point, Feature, FeatureCollection, dump, Polygon, load
import geojson
from shapely.geometry import shape, LineString, MultiLineString, Polygon, mapping
import shapely
from shapely.ops import transform, nearest_points
from shapely import wkt
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
from osm_fieldwork.convert import escape
from osm_fieldwork.parsers import ODKParsers
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
# from spellchecker import SpellChecker
from osm_rawdata.pgasync import PostgresClient
from tqdm import tqdm
import tqdm.asyncio
import xmltodict
from numpy import arccos, array
from numpy.linalg import norm
import math
import numpy

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
# Try doubling the number of cores, since the CPU load is
# still reasonable.
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
# Shapely.distance doesn't like duplicate points
warnings.simplefilter(action='ignore', category=RuntimeWarning)

# A function that returns the 'year' value:
def distSort(data: list):
    """
    Args:
        data (list): The data to sort
    """
    return data['dist']

def hitsSort(data: list):
    """
    Args:
        data (list): The data to sort
    """
    return data['hits']

def conflateThread(primary: list,
                   secondary: list,
                   informal: bool = False,
                   threshold: float = 7.0,
                   spellcheck: bool = True,
                   ) -> list:
    """
    Conflate features from ODK against all the features in OSM.

    Args:
        primary (list): The external dataset to conflate
        seconday (list): The secondzry dataset, probably existing OSM data
        threshold (int): Threshold for distance calculations
        informal (bool): Whether to dump features in OSM not in external data
        spellcheck (bool): Whether to also spell check string values

    Returns:
        (list):  The conflated output
    """
    # log.debug(f"Dispatching thread ")

    #timer = Timer(text="conflateFeatures() took {seconds:.0f}s")

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
    newdata = list()
    # New features not in OSM always use negative IDs
    odkid = -100
    osmid = 0
    nodes = dict()
    version = 0
    cutils = Conflator()
    i = 0

    log.info(f"The primary dataset has {len(primary)} entries")
    log.info(f"The secondary dataset has {len(secondary)} entries")
    
    # Progress bar
    pbar = tqdm.tqdm(primary)
    for entry in pbar:
    # for entry in primary:
        i += 1
        # timer.start()
        confidence = 0
        maybe = list()

        for existing in secondary:
            odktags = dict()
            osmtags = dict()
            feature = dict()
            newtags = dict()
            # log.debug(f"ENTRY: {entry["properties"]}")
            # log.debug(f"EXISTING: {existing["properties"]}")
            if existing["geometry"] is not None:
                if existing["geometry"]["type"] == "Point":
                    data.append(existing)
                    continue
            geom = None
            # We could probably do this using GeoPandas or gdal, but that's
            # going to do the same brute force thing anyway.

            # If the input file is in OSM XML format, we don't want to
            # conflate the nodes with no tags. They are used to build
            # the geometry for the way, and after that aren't needed anymore.
            # If the node has tags, then it's a POI, which we do conflate.
            # log.debug(entry)
            if entry["geometry"] is None or existing["geometry"] is None:
                # Obviously can't do a distance comparison is a geometry is missing
                continue
            if entry["geometry"]["type"] == "Point" and len(entry["properties"]) <= 2:
                continue
            if existing["geometry"]["type"] == "Point" and len(existing["properties"]) <= 2:
                continue

            dist = float()
            slope = float()
            hits = 0

            try:
                dist = cutils.getDistance(entry, existing)
            except:
                log.error(f"getDistance() just had a weird error")
                log.error(f"ENTRY: {entry["properties"]}")
                log.error(f"EXISTING: {existing["properties"]}")
                # breakpoint()
                continue

            # log.debug(f"ENTRY: {dist}: {entry["properties"]}")
            # log.debug(f"EXISTING: {existing["properties"]}")
            if dist <= threshold:
                angle = 0.0
                try:
                    slope, angle = cutils.getSlope(entry, existing)
                except:
                    log.error(f"getSlope() just had a weird error")
                    log.error(f"ENTRY: {entry["properties"]}")
                    log.error(f"EXISTING: {existing["properties"]}")
                    # breakpoint()
                    # slope, angle = cutils.getSlope(entry, existing)
                    break
                # log.debug(f"DIST: {dist}, ANGLE: {angle}, SLOPE: {slope}")
                # log.debug(f"PRIMARY: {entry["properties"]}")
                # log.debug(f"SECONDARY: {existing["properties"]}")
                hits, tags = cutils.checkTags(entry, existing)
                # log.debug(f"HITS2: {hits}")
                angle_threshold = 20.0
                slope_threshold = 4.0
                name1 = None
                name2 = None
                if "name" in existing["properties"]:
                    name2 = existing["properties"]["name"]
                if "name" in entry["properties"]:
                    name1 = entry["properties"]["name"]
                log.debug(f"DIST: {dist}, SLOPE: {slope:.3f}, Angle: {angle:.3f} - {name1} == {name2}")
                # if name1 == "West Fork Road":
                # breakpoint()
                if hits == 0 and (abs(angle) > angle_threshold or abs(slope) > slope_threshold):
                    continue
                if hits == 1 and abs(angle) < 15 and abs(slope) < 1:
                    log.debug(f"Name matched, not geom")
                    log.error(f"ENTRY: {entry["properties"]}")
                    log.error(f"EXISTING: {existing["properties"]["id"]}")
                    # FIXME parallel roads
                    break
                if hits == 2 and abs(angle) < angle_threshold and abs(slope) < slope_threshold:
                    if tags["ratio"] == 100:
                        log.debug(f"Name matched and ref matched")
                        log.error(f"ENTRY: {entry["properties"]}")
                        log.error(f"EXISTING: {existing["properties"]["id"]}")
                        break
                if hits == 0 and angle == 0.0 and slope == 0.0 and dist == 0.0:
                    print(f"Geometry matched, not name")
                    log.error(f"ENTRY: {entry["properties"]}")
                    log.error(f"EXISTING: {existing["properties"]["id"]}")
                    hits += 1
                    break

                if hits == 3:
                    if entry['properties'] != existing['properties']:
                        # Only add the feature to the output if there are
                        # differences in the tags. If they are identical,
                        # ignore it as no changes need to be made.
                        data.append(Feature(geometry=geom, properties=entry["properties"]))
                        log.error(f"ENTRY: {entry["properties"]}")
                        log.error(f"EXISTING: {existing["properties"]["id"]}")
                        break
                    else:
                        log.debug(f"Perfect match! {entry['properties']}")
                        break

                maybe.append({"hits": hits, "dist": dist, "angle": angle, "slope": slope, "odk": entry, "osm": existing})
                tags["hits"] = str(hits)
                tags["dist"] = str(dist)
                tags["slope"] = str(slope)
                tags["angle"] = str(angle)
                data.append(Feature(geometry=geom, properties=tags))
                # cache all OSM features within our threshold distance
                # These are needed by ODK, but duplicates of other fields,
                # so they aren't needed and just add more clutter.
                # log.debug(f"DIST: {dist / 1000}km. {dist}m")
                # maybe.append({"hits": hits, "dist": dist, "slope": slope, "angle": angle, "hits": hits, "odk": entry, "osm": existing})
                # don't keep checking every highway, although testing seems
                # to show 99% only have one distance match within range.
                if len(maybe) >= 5:
                    # FIXME: it turns out sometimes the other nearby highways are
                    # segments of the same highway, but the tags only get added
                    # to the closest segment.
                    log.debug(f"Have enough matches.")
                    break

        hits = 0
        threshold = 2
        if len(maybe) > 0:
            # FIXME: Sometimes all the maybes are segment of the same
            # highways. Right now only one gets the tags merged, this
            # should be fixed so all nearby segmernts get tagged.

            # cache the refs to use in the OSM XML output file
            refs = list()
            odk = dict()
            osm = dict()
            slope = float()
            dist = float()
            # There are two parameters used to decide on the probably
            # match. If we have at least 2 hits, it's very likely a
            # good match, 3 is a perfect match.
            best = None
            maybe.sort(key=hitsSort)
            hits = maybe[len(maybe) - 1]["hits"]
            if hits >= threshold:
                best = maybe[len(maybe) - 1]
                odk = best["odk"]["properties"]
                osm = best["osm"]["properties"]
            else:
                # If no hits, the OSM data is probably limited to
                # highway=track. so then get the closest one.
                maybe.sort(key=distSort)
                best = maybe[0]
                odk = best["odk"]["properties"]
                osm = best["osm"]["properties"]
            # log.debug(f"HITS1: {hits}")
            # tags['fixme'] = "Don't upload this to OSM without validation!"
            if "refs" in osm:
                tags["refs"] = osm["refs"]
            geom = best["odk"]["geometry"]
            if "osm_id" in  osm:
                tags["id"] =  osm["osm_id"]
            elif "id" in  osm:
                tags["id"] =  osm["id"]
            if "version" in osm:
                tags["version"] = osm["version"]
            else:
                tags["version"] = 1
            tags["hits"] = hits
            tags["dist"] = str(best["dist"])
            tags["slope"] = str(best["slope"])
            tags["angle"] = str(best["angle"])
            data.append(Feature(geometry=geom, properties=tags))
            # If no hits, it's new data. ODK data is always just a POI for now
        else:
            entry["properties"]["version"] = 1
            entry["properties"]["informal"] = "yes"
            entry["properties"]["fixme"] = "New features should be imported following OSM guidelines."
            # entry["properties"]["slope"] = slope
            # entry["properties"]["dist"] = dist
            # log.debug(f"FOO({dist}): {entry}")
            newdata.append(entry)

        # timer.stop()

    log.debug(f"NEW: {len(newdata)}")
    return [data, newdata]

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

    def getSlope(self,
            newdata: Feature,
            olddata: Feature,
            ) -> float:

        # timer = Timer(text="getSlope() took {seconds:.0f}s")
        # timer.start()
        # old = numpy.array(olddata["geometry"]["coordinates"])
        # oldline = shape(olddata["geometry"])
        angle = 0.0
        # newline = shape(newdata["geometry"])
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:3857')
            )
        newobj = transform(project.transform, shape(newdata["geometry"]))
        oldobj = transform(project.transform, shape(olddata["geometry"]))
        # if newline.type == "MultiLineString":
        #     lines = newline.geoms
        # elif newline.type == "GeometryCollection":
        #     lines = newline.geoms
        # else:
        #     lines = MultiLineString([newline]).geoms
        bestslope = None
        bestangle = None
        for segment in [newobj]:
            #new = numpy.array(newdata["geometry"]["coordinates"])
            #newline = shape(newdata["geometry"])
            points = shapely.get_num_points(segment)
            if points == 0:
                return -0.1, -0.1
            # log.debug(f"POINTS: {shapely.get_num_points(segment)} vs {shapely.get_num_points(oldline)}")
            offset = 2
            # Get slope of the new line
            start = shapely.get_point(segment, offset)
            if not start:
                return float(), float()
            x1 = start.x
            y1 = start.y
            end = shapely.get_point(segment, points - offset)
            x2 = end.x
            y2 = end.y
            if start == end:
                log.debug(f"The geometries are identical!")
                return 0.0, 0.0
            slope1 = (y2 - y1) / (x2 - x1)

            # Get slope of the old line
            start = shapely.get_point(oldobj, offset)

            if not start:
                return float(), float()
            x1 = start.x
            y1 = start.y
            end = shapely.get_point(oldobj, shapely.get_num_points(oldobj) - offset)
            x2 = end.x
            y2 = end.y
            if start == end:
                log.debug(f"The geometries are identical!")
                return 0.0, 0.0

            if (x2 - x1) == 0.0:
                return 0.0, 0.0
            slope2 = (y2 - y1) / (x2 - x1)
            # timer.stop()
            slope = slope1 - slope2

            # Calculate the angle between the linestrings
            angle = math.degrees(math.atan((slope2-slope1)/(1+(slope2*slope1))))
            name1 = "None"
            name2 = "None"
            if math.isnan(angle):
                angle = 0.0
            if "name" in newdata["properties"]:
                name1 = newdata["properties"]["name"]
            if "name" in olddata["properties"]:
                name2 = olddata["properties"]["name"]
            try:
                if math.isnan(slope):
                    slope = 0.0
                if math.isnan(angle):
                    angle = 0.0

                # Find the closest segment
                if bestangle is None:
                    bestangle = angle
                elif angle < bestangle:
                    print(f"BEST: {best} < {dist}")
                    bestangle = angle
            except:
                print("BREAK")
                breakoint()

        return slope, bestangle # angle
      
    def getDistance(self,
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
        # timer = Timer(text="getDistance() took {seconds:.0f}s")
        # timer.start()
        # dist = shapely.hausdorff_distance(center, wkt)
        dist = float()

        # Transform so the results are in meters instead of degress of the
        # earth's radius.
        project = pyproj.Transformer.from_proj(
            pyproj.Proj(init='epsg:4326'),
            pyproj.Proj(init='epsg:3857')
            )
        newobj = transform(project.transform, shape(newdata["geometry"]))
        oldobj = transform(project.transform, shape(olddata["geometry"]))

        # FIXME: we shouldn't ever get here...
        if oldobj.type == "MultiLineString":
            log.error(f"MultiLineString unsupported!")

        if newobj.type == "MultiLineString":
            lines = newobj.geoms
        elif newobj.type == "GeometryCollection":
            lines = newobj.geoms
        else:
            lines = MultiLineString([newobj]).geoms

        # dists = list()
        best = None
        for segment in lines:
            if oldobj.geom_type == "LineString" and segment.geom_type == "LineString":
                # Compare two highways
                # if oldobj.within(segment):
                #    log.debug(f"CONTAINS")
                dist = segment.distance(oldobj)
            elif oldobj.geom_type == "Point" and segment.geom_type == "LineString":
                # We only want to compare LineStrings, so force the distance check
                # to be False
                dist = 12345678.9
            elif oldobj.geom_type == "Point" and segment.geom_type == "Point":
                dist = segment.distance(oldobj)
            elif oldobj.geom_type == "Polygon" and segment.geom_type == "Polygon":
                # compare two buildings
                pass
            elif oldobj.geom_type == "Polygon" and segment.geom_type == "Point":
                # Compare a point with a building, used for ODK Collect data
                center = shapely.centroid(oldobj)
                dist = segment.distance(center)
            elif oldobj.geom_type == "Point" and segment.geom_type == "LineString":
                dist = segment.distance(oldobj)
            elif oldobj.geom_type == "LineString" and segment.geom_type == "Point":
                dist = segment.distance(oldobj)

            # Find the closest segment
            if best is None:
                best = dist
            elif dist < best:
                # log.debug(f"BEST: {best} < {dist}")
                best = dist

        # timer.stop()
        return best # dist # best

    def checkTags(self,
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
        match_threshold = 85
        match = ["name", "ref", "ref:usfs"]
        hits = 0
        props = dict()
        id = 0
        version = 0
        props = extfeat['properties'] | osm['properties']
        # ODK Collect adds these two tags we don't need.
        if "title" in props:
            del props["title"]
        if "label" in props:
            del props["label"]

        if "id" in props:
            # External data not from an OSM source always has
            # negative IDs to distinguish it from current OSM data.
            id = int(props["id"])
        else:
            id -= 1
            props["id"] = id

        if "version" in props:
            # Always use the OSM version if it exists, since it gets
            # incremented so JOSM see it's been modified.
            props["version"] = int(version)
            # Name may also be name:en, name:np, etc... There may also be
            # multiple name:* values in the tags.
        else:
            props["version"] = 1

        for key in match:
            if "highway" in osm["properties"]:
                # Always use the value in the secondary, which is
                # likely OSM.
                props["highway"] = osm["properties"]["highway"]
            if key not in props:
                continue

            # Usually it's the name field that has the most variety in
            # in trying to match strings. This often is differences in
            # capitalization, singular vs plural, and typos from using
            # your phone to enter the name. Course names also change
            # too so if it isn't a match, use the new name from the
            # external dataset.
            if key in osm["properties"] and key in extfeat["properties"]:
                # Sometimes there will be a word match, which returns a
                # ratio in the low 80s. In that case they should be
                # a similar length.
                length = len(extfeat["properties"][key]) - len(osm["properties"][key])
                ratio = fuzz.ratio(extfeat["properties"][key].lower(), osm["properties"][key].lower())
                if ratio > match_threshold and length <= 3:
                    hits += 1
                    props["ratio"] = ratio
                    props[key] = extfeat["properties"][key]
                    if ratio != 100:
                        # Often the only difference is using FR or FS as the
                        # prefix. In that case, see if the ref matches.
                        if key[:3] == "ref":
                            # This assume all the data has been converted
                            # by one of the utility programs, which enfore
                            # using the ref:usfs tag.
                            tmp = extfeat["properties"]["ref:usfs"].split(' ')
                            extref = tmp[1].upper()
                            tmp = osm["properties"]["ref:usfs"].split(' ')
                            newref = tmp[1].upper()
                            # log.debug(f"REFS: {extref} vs {newref}: {extref == newref}")
                            if extref == newref:
                                hits += 1
                                # Many minor changes of FS to FR don't require
                                # caching the exising value as it's only the
                                # prefix that changed. It always stayes in this
                                # range.
                                if osm["properties"]["ref:usfs"][:3] == "FS " and ratio > 80 and ratio < 90:
                                    # log.debug(f"Ignoring old ref {osm["properties"]["ref:usfs"]}")
                                    continue
                        # For a fuzzy match, cache the value from the
                        # secondary dataset and use the value in the
                        # primary dataset.
                        props[f"old_{key}"] = osm["properties"][key]

        # print(props)
        return hits, props

    def loadFile(
        self,
        osmfile: str,
    ) -> list:
        """
        Read a OSM XML file and convert it to GeoJson for consistency.

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
                        # Drop all the TIGER tags based on
                        # https://wiki.openstreetmap.org/wiki/TIGER_fixup
                        if tag["@k"] in properties:
                            if properties[tag["@k"]][:7] == "tiger:":
                                continue
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
            attrs = dict()
            properties = {
                "id": int(way["@id"]),
            }
            refs = list()
            if "nd" in way:
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
            if geom is None:
                breakpoint()
            # log.debug(f"WAY: {properties}")
            alldata.append(Feature(geometry=geom, properties=properties))

        return alldata

    def conflateData(self,
                    odkspec: str,
                    osmspec: str,
                    threshold: float = 3.0,
                    informal: bool = False,
                    ) -> list:
        """
        Open the two source files and contlate them.

        Args:
            odkspec (str): The external data uri
            osmspec (str): The existing OSM data uri
            threshold (float): Threshold for distance calculations in meters
            informal (bool): Whether to dump features in OSM not in external data

        Returns:
            (list):  The conflated output
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        odkdata = list()
        osmdata = list()

        result = list()
        # if odkspec[:3].lower() == "pg:":
        #     db = GeoSupport(odkspec[3:])
        #     result = await db.queryDB()
        # else:
        odkdata = self.parseFile(odkspec)

        # if osmspec[:3].lower() == "pg:":
        #     db = GeoSupport(osmspec[3:])
        #     result = await db.queryDB()
        # else:
        osmdata = self.parseFile(osmspec)

        entries = len(odkdata)
        chunk = round(entries / cores)

        alldata = list()
        tasks = list()

        log.info(f"The primary dataset has {len(odkdata)} entries")
        log.info(f"The secondary dataset has {len(osmdata)} entries")

        # Make threading optional for easier debugging
        single = False

        if single:
            alldata = conflateThread(odkdata, osmdata)
        else:
            futures = list()
            with concurrent.futures.ProcessPoolExecutor(max_workers=cores) as executor:
                for block in range(0, entries, chunk):
                    future = executor.submit(conflateThread,
                            odkdata[block:block + chunk - 1],
                            osmdata,
                            informal
                            )
                    futures.append(future)
                #for thread in concurrent.futures.wait(futures, return_when='ALL_COMPLETED'):
                for future in concurrent.futures.as_completed(futures):
                    log.debug(f"Waiting for thread to complete..")
                    alldata += future.result()

            executor.shutdown()

        timer.stop()

        return alldata

    def dump(self):
        """
        Dump internal data for debugging.
        """
        print(f"Data source is: {self.dburi}")
        print(f"There are {len(self.data)} existing features")
        # if len(self.versions) > 0:
        #     for k, v in self.original.items():
        #         print(f"{k}(v{self.versions[k]}) = {v}")

    def parseFile(self,
                filespec: str,
                ) ->list:
        """
        Parse the input file based on it's format.

        Args:
            filespec (str): The file to parse

        Returns:
            (list): The parsed data from the file
        """
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
                 data: list,
                 filespec: str,
                 ):
        """
        Write the data to an OSM XML file.

        Args:
            data (list): The list of GeoJson features
            filespec (str): The output file name
        """
        osm = OsmFile(filespec)
        negid = -100
        id = -1
        out = str()
        newmvum = list()
        for entry in data:
            version = 1
            tags = entry["properties"]
            if "osm_id" in tags:
                id = tags["osm_id"]
            elif "id" in tags:
                id = tags["id"]
            elif "id" not in tags:
                # There is no id or version for non OSM features
                id -= 1
            if "version" in entry["properties"]:
                version = int(entry["properties"]["version"])
                version += 1
            # if id == 814085818:
            #    breakpoint()
            attrs = {"id": id, "version": version}
            # These are OSM attributes, not tags
            if "id" in tags:
                del tags["id"]
            if "version" in tags:
                del tags["version"]
            item = {"attrs": attrs, "tags": tags}
            # if entry["geometry"]["type"] == "LineString" or entry["geometry"]["type"] == "Polygon":
            # print(entry)
            out = str()
            if entry["geometry"] is not None and entry["geometry"]["type"] == "Point":
                # It's a node referenced by a way
                item["attrs"]["lon"] = entry["geometry"]["coordinates"][0]
                item["attrs"]["lat"] = entry["geometry"]["coordinates"][1]
                if "timestamp" in item["tags"]:
                    item["attrs"]["timestamp"] = item["tags"]["timestamp"]
                    del item["tags"]["timestamp"]
                # referenced nodes should have no tags
                del item["tags"]
                # FIXME: determine if we need to write nodes
                # out = osm.createNode(item, False)
                continue
            else:
                # OSM ways don't have a geometry, just references to node IDs.
                # The OSM XML file won't have any nodes, so at first won't
                # display in JOSM until you do a File->"Update modified",
                if "refs" not in tags:
                    # log.debug(f"No Refs, so new MVUM road not in OSM {tags}")
                    # tags["fixme"] = "New road from MVUM, don't add!"
                    # FIXME: for now we don't do anything with new roads from
                    # an external dataset, because that would be an import.
                    newmvum.append(entry)
                    continue
                if len(tags['refs']) > 0:
                    if type(tags["refs"]) != list:
                        item["refs"] = eval(tags["refs"])
                    else:
                        item["refs"] = tags["refs"]
                    del tags["refs"]
                    out = osm.createWay(item, True)
            if len(out) > 0:
                osm.write(out)

    def writeGeoJson(self,
                 data: dict,
                 filespec: str,
                 ):
        """
        Write the data to a GeoJson file.

        Args:
            data (dict): The list of GeoJson features
            filespec (str): The output file name
        """
        file = open(filespec, "w")
        fc = FeatureCollection(data)
        geojson.dump(fc, file, indent=4)

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
        elif "id" in osm["attrs"]:
            id = osm["attrs"]["id"]
        props = {"id": id}
        if "version" in osm["attrs"]:
            props["version"] = osm["attrs"]["version"]

        props.update(osm["tags"])
        # It's a way, so no coordinate
        if "refs" in osm:
            return Feature(properties=props)
        else:
            geom = Point((float(osm["attrs"]["lon"]), float(osm["attrs"]["lat"])))

            return Feature(geometry=geom, properties=props)

def main():
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
    parser.add_argument("-s", "--secondary", help="The secondary dataset")
    parser.add_argument("-q", "--query", help="Custom SQL when using a database")
    parser.add_argument("-c", "--config", default="highway", help="The config file for the SQL query")
    parser.add_argument("-p", "--primary", required=True, help="The primary dataset")
    parser.add_argument("-t", "--threshold", default=2.0, help="Threshold for distance calculations")
    parser.add_argument("-i", "--informal", help="Dump features not in official sources")
    parser.add_argument("-o", "--outfile", default="conflated.geojson", help="Output file from the conflation")
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

    if not args.secondary and not args.uri:
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

    conflate = Conflator(args.secondary, args.boundary)
    # if args.secondary[:3].lower() == "pg:":
    #     await conflate.initInputDB(args.config, args.secondary[3:])

    # if args.primary[:3].lower() == "pg:":
    #     await conflate.initInputDB(args.config, args.secondary[3:])

    data = conflate.conflateData(args.primary, args.secondary, float(args.threshold), args.informal)

    # path = Path(args.outfile)
    osmout  = args.outfile.replace(".geojson", "-out.osm")

    conflate.writeOSM(data[0], osmout)
    log.info(f"Wrote {osmout}")

    jsonout = args.outfile.replace(".geojson", "-out.geojson")
    conflate.writeGeoJson(data[0], jsonout)
    log.info(f"Wrote {jsonout}")

    jsonout = args.outfile.replace(".geojson", "-new.geojson")
    conflate.writeGeoJson(data[1], jsonout)

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
    #loop = asyncio.new_event_loop()
    #asyncio.set_event_loop(loop)
    #loop.run_until_complete(main())
