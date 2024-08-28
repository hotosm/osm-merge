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
from shapely.geometry import shape, LineString, Polygon, mapping
import shapely
from shapely.ops import transform
from shapely import wkt
from osm_fieldwork.osmfile import OsmFile
from osm_fieldwork.parsers import ODKParsers
import asyncio
from codetiming import Timer
from pathlib import Path
from osm_fieldwork.parsers import ODKParsers
from pathlib import Path
from spellchecker import SpellChecker
from osm_rawdata.pgasync import PostgresClient
import xmltodict
from threading import Thread
from progress.bar import Bar, PixelBar

# Instantiate logger
log = logging.getLogger(__name__)


async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="fix names",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-o", "--outfile", default="out.geojson", help="Output file from the conflation")
    parser.add_argument("-i", "--infile", required=True, help="Input file to fix")

    args = parser.parse_args()

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

    path = Path(args.infile)
    if path.suffix == ".geojson":
        file = open(args.infile, "r")
        indata = geojson.load(file)
        data = indata["features"]
        file.close()
    elif path.suffix == ".osm":
        osm = OsmFile()
        indata = osm.loadFile(args.infile)
        data = indata
    else:
        log.error("Unsupport file type!")

    features = list()
    if "features" in data:
        spin = Bar('Processing...', max=len(data['features']))
    else:
        spin = Bar('Processing...', max=len(data))
    for feature in data:
        tags = {"name": None, "ref:usfs": None, "ref": None}
        matched = False
        name = None
        ref = None
        if "properties" in feature:
            if "name" in feature["properties"]:
                name = feature["properties"]["name"]
            else:
                continue
            if "ref" in feature["properties"]:
                ref = feature["properties"]["ref"]
        elif "tags" in feature:
            if "name" in feature["tags"]:
                name = feature["tags"]["name"]
            if "name" not in feature["tags"] and "name_1" in feature["tags"]:
                name = feature["tags"]["name_1"]
            if "ref" in feature["tags"]:
                ref = feature["tags"]["ref"]

        if ref is not None:
            if ref.find(';') > 0:
                tmp = ref.split(';')
                log.debug(f"REF: {ref}")
                tags["ref"] = tmp[0]
                tags["ref:usfs"] = tmp[1]

        if name is None:
            features.append(feature)
            continue

        # log.debug(f"NAME: {name}")
        ref = "[0-9]+[.a-z]"
        pat = re.compile(ref)
        if pat.match(name.lower()):
            # log.debug(f"MATCHED: {pat.pattern}")
            tags["ref:usfs"] = f"FR {name.title()}"
            matched = True

        pat = re.compile(f"fire road")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] = f"FR {tmp[2].title()}"
            matched = True

        pat = re.compile(f"county road")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref"] = f"CR {tmp[2].title()}"
            matched = True

        pat = re.compile(f"fs.* road")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] = f"FR {tmp[2].title()}"
            matched = True

        pat = re.compile(f"fs[hr] ")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] = f"FR {tmp[1].title()}"
            matched = True

        # pat = re.compile(f"fsr road")
        # if pat.match(name.lower()) and not matched:
        #     # log.debug(f"MATCHED: {pat.pattern}")
        #     tmp = name.split(' ')
        #     tags["ref:usfs"] = f"FR {tmp[2].title()}"
        #     matched = True

        pat = re.compile(f"usf.* road")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] = f"FR {tmp[2].title()}"
            matched = True

        pat = re.compile(f".*forest service road")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            if len(tmp) == 3:
                tags["ref:usfs"] = f"FR {tmp[2].title()}"
            elif len(tmp) == 4:
                tags["ref:usfs"] = f"FR {tmp[3].title()}"
            elif len(tmp) == 5:
                tags["ref:usfs"] = f"FR {tmp[4].title()}"
            matched = True

        pat = re.compile(f"fr ")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tags["ref:usfs"] = f"FR {tmp[1].title()}"
            matched = True

        pat = re.compile(f"fs ")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] =  f"FR {tmp[1].title()}"
            matched = True

        pat = re.compile(f"forest road ")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] =  f"FR {tmp[2].title()}"
            matched = True

        pat = re.compile(f"usfs trail ")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] = f"FR {tmp[2].title()}"
            matched = True

        pat = re.compile(f".*fsr{ref}")
        if pat.match(name.lower()) and not matched:
            # log.debug(f"MATCHED: {pat.pattern}")
            tmp = name.split(' ')
            tags["ref:usfs"] = f"FR {tmp[2].title()}"

        if matched:
            for key, value in tags.items():
                if value is not None:
                    if "properties" in feature:
                        del feature["properties"]["name"]
                        feature["properties"][key] = value
                    elif "tags" in feature:
                        if "name" in feature["tags"]:
                            del feature["tags"]["name"]
                        feature["tags"][key] = value
            features.append(feature)
        else:
            features.append(feature)

        # log.debug(f"\t{tags}")

    if path.suffix == ".geojson":
        outdata = FeatureCollection(features)
        file = open(args.outfile, "w")
        geojson.dump(outdata, file)
        file.close()
        log.info(f"Wrote {args.outfile}")
    else:
        path = Path(args.outfile)
        outosm = OsmFile(f"{path.stem}-out.osm")
        out = list()
        for entry in features:
            if "tiger:cfcc" in entry["tags"]:
                del entry["tags"]["tiger:cfcc"]
            if "tiger:county" in entry["tags"]:
                del entry["tags"]["tiger:county"]
            if "tiger:name_base" in entry["tags"]:
                del entry["tags"]["tiger:name_base"]
            if "tiger:name_base_1" in entry["tags"]:
                del entry["tags"]["tiger:name_base_1"]
            if "tiger:name_type" in entry["tags"]:
                del entry["tags"]["tiger:name_type"]
            if "tiger:name_type_1" in entry["tags"]:
                del entry["tags"]["tiger:name_type_1"]
            if "tiger:reviewed" in entry["tags"]:
                del entry["tags"]["tiger:reviewed"]
            if "tiger:tlid" in entry["tags"]:
                del entry["tags"]["tiger:tlid"]
            if "tiger:source" in entry["tags"]:
                del entry["tags"]["tiger:source"]
            if "tiger:separated" in entry["tags"]:
                del entry["tags"]["tiger:separated"]
            if "tiger:upload_uuid" in entry["tags"]:
                del entry["tags"]["tiger:upload_uuid"]
            if "name_1" in entry["tags"]:
                del entry["tags"]["name_1"]
            if "lat" not in entry["attrs"]:
                out.append(osm.createWay(entry, True))
            else:
                out.append(osm.createNode(entry, True))
        outosm.write(out)
        log.info(f"Wrote {path.stem}.osm")


if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
