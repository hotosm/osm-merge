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
import pyproj
import asyncio
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep
from thefuzz import fuzz, process
from pathlib import Path
from tqdm import tqdm
import tqdm.asyncio
from progress.bar import Bar, PixelBar

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']

# shut off warnings from pyproj
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class MVUM(object):
    def __init__(self,
                 filespec: str = None,
                 ):
        self.file = None
        if filespec is not None:
            self.file = open(filespec, "r")

    def convert(self,
                filespec: str = None,
                ) -> list:

        # FIXME: read in the whole file for now
        if filespec is not None:
            file = open(filespec, "r")
        else:
            file = self.file

        data = geojson.load(file)

        spin = Bar('Processing...', max=len(data['features']))

        highways = list()
        for entry in data["features"]:
            spin.next()

            geom = entry["geometry"]
            id = 0
            sym = 0
            op = None
            surface = str()
            name = str()
            props = dict()
            # print(entry["properties"])
            if entry["properties"] is None or entry is None:
                continue
            if "ID" in entry["properties"]:
                id = f"FR {entry['properties']['ID']}"
                # For consistency, capitalize the last character
                props["ref:usfs"] = id.upper()
            if "NAME" in entry["properties"] and entry["properties"]["NAME"] is not None:
                title = entry["properties"]["NAME"].title()
                name = str()
                # Fix some common abbreviations
                for word in title.split():
                    if "Cr" == word:
                        name += "Creek "
                    elif "Cr." == word:
                        name += "Creek "
                    elif "Ck." == word:
                        name += "Creek "
                    elif "Crk" == word:
                        name += "Creek "
                    elif "Cg" == word:
                        name += "Campground "
                    elif "Rd" == word:
                        name += "Road"
                    elif "Disp" == word:
                        name += "Dispersed "
                    elif "Rd." == word:
                        name += "Road"
                    elif "Mt" == word:
                        name += "Mountain "
                    elif "Lk" == word:
                        name += "Lake"
                    elif "N" == word:
                        name += "North"
                    elif "W" == word:
                        name += "West"
                    elif "E" == word:
                        name += "East"
                    elif "S" == word:
                        name += "South"
                    elif "Mtn" == word:
                        name += "Mountain"
                    else:
                        name += f" {word} "
                if len(name) == 0:
                    name = title
                newname = str()
                if name.find(" Road") <= 0:
                    newname = f"{name} Road".replace('  ', ' ').strip()
                else:
                    newname = name.replace('  ', ' ').strip()
                # the < causes osmium to choke...
                props["name"] = newname.replace("<50", "&lt;50")
                # log.debug(f"NAME: {props["name"]}")

            # https://www.fs.usda.gov/Internet/FSE_DOCUMENTS/stelprd3793545.pdf

            if "OPER_MAINT_LEVEL" in entry["properties"] and entry["properties"]["OPER_MAINT_LEVEL"] is not None:
                if entry["properties"]["OPER_MAINT_LEVEL"][:3] != "NA ":
                    op = int(entry["properties"]["OPER_MAINT_LEVEL"][:1])
                    if op == 1:
                        props["access"] = "no"
                    elif op == 2:
                        props["smoothness"] = "very_bad"
                    elif op == 3:
                        props["smoothness"] = "good"
                    elif op == 4:
                        props["smoothness"] = "bad"
                    elif op == 5:
                        props["smoothness"] = "excellent"

            if "PRIMARY_MAINTAINER" in entry["properties"] and  entry["properties"]["PRIMARY_MAINTAINER"] is not None:
                if entry["properties"]["PRIMARY_MAINTAINER"] == "FS - FOREST SERVICE":
                    props["operator"] = "US Forest Service"
                else:
                    props["operator"] = entry["properties"]["PRIMARY_MAINTAINER"].title()

            if "SYMBOL_NAME" in entry["properties"]:
                if entry["properties"]["SYMBOL_NAME"] is None:
                    continue
                op = entry["properties"]["SYMBOL_NAME"][:4]
                if op == "Road":
                    props["smoothness"] = "very bad"
                elif op == "Pave":
                    props["smoothness"] = "good"
                elif op == "High":
                    props["smoothness"] = "excellent"
                elif op == "Dirt":
                    props["surface"] = "dirt"
                elif op == "Grav":
                    props["surface"] = "gravel"
                elif op == "Pave":
                    props["surface"] = "paved"

            # if "SBS_SYMBOL" in entry["properties"] and op is None:
            #     if "Not Maintained for" in entry["properties"]["SBS_SYMBOL"]:
            #         props["smoothness"] = "very bad"
            #     else:
            #         sym = entry["properties"]
            if "SURFACE_TYPE" in entry["properties"]:
                surface = entry["properties"]["SURFACE_TYPE"]
                if surface is not None:
                    if surface[:3] == "NAT":
                        props["surface"] = "dirt"
                    elif surface[:3] == "IMP" or surface[:5] == "CSOIL":
                        props["surface"] = "compacted"
                    elif surface[:3] == "AGG":
                        props["surface"] = "gravel"
                    elif surface[:2] == "AC":
                        props["surface"] = "gravel"
                    elif surface[:3] == "BST" or surface[:2] == "P ":
                        props["surface"] = "paved"

            if "HIGH_CLEARANCE_VEHICLE" in entry["properties"]:
                if entry["properties"]["HIGH_CLEARANCE_VEHICLE"] is not None:
                    props["4wd_only"] = "yes"

            if "SEASONAL" in entry["properties"]:
                if entry["properties"]["SEASONAL"] is None:
                    continue
                elif "yearlong" == entry["properties"]["SEASONAL"]:
                    props["seasonal"] = "no"
                elif "seasonal" == entry["properties"]["SEASONAL"].lower():
                    props["seasonal"] = "yes"
                else:
                    props["seasonal"] = "yes"

            if geom is not None:
                highways.append(Feature(geometry=geom, properties=props))
            # print(props)

        return FeatureCollection(highways)
    
def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="mvum",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts MVUM highway data into OSM tagging",
        epilog="""
This program processes the MVUM data. It will convert the MVUM dataset
to using OSM tagging schema so it can be conflated. Abbreviations are
discouraged in OSM, so they are expanded. Most entries in the MVUM
dataset are ignored. For fixing the TIGER mess, all that is relevant
are the name and the USFS reference number. The surface and smoothness
tags are also converted, but should never overide what is in OSM, as the
OSM values for these may be more recent. And the values change over time,
so what is in the MVUM dataset may not be accurate. These tags are converted
primarily as an aid to navigation when ground-truthing, since it's usually
good to avoid any highway with a smoothness of "very bad" or worse.

    For Example: 
        mvum.py -v -c -i WY_RoadsMVUM.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Output file from the conflation")
    parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert MVUM feature to OSM feature")
    parser.add_argument("-o", "--outfile", default="out.geojson", help="Output file")

    args = parser.parse_args()

    # if verbose, dump to the terminal.
    log_level = os.getenv("LOG_LEVEL", default="INFO")
    if args.verbose is not None:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format=("%(asctime)s.%(msecs)03d [%(levelname)s] " "%(name)s | %(funcName)s:%(lineno)d | %(message)s"),
        datefmt="%y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    mvum = MVUM()
    if args.convert and args.convert:
        data = mvum.convert(args.infile)

        file = open(args.outfile, "w")
        geojson.dump(data, file, indent=4)
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(main())
    main()
