#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024 OpenStreetMap US
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

#
# This program proccesses the National Forest Service MVUM dataset. That
# processing includes deleting unnecessary tags, and converting the
# tags to an OSM standard for conflation.
#

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
from osm_merge.yamlfile import YamlFile

import osm_merge as om
rootdir = om.__path__[0]

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
                 dataspec: str = None,
                 yamlspec: str = "utilities/mvum.yaml",
                 ):
        """
        This class processes the MVUM dataset.

        Args:
            dataspec (str): The input data to convert
            yamlspec (str): The YAML config file for converting data

        Returns:
            (MVUM): An instance of this class
        """
        self.file = None
        if dataspec is not None:
            self.file = open(dataspec, "r")

        yaml = f"{rootdir}/{yamlspec}"
        if not os.path.exists(yaml):
            log.error(f"{yaml} does not exist!")
            quit()
        
        file = open(yaml, "r")
        self.yaml = YamlFile(f"{yaml}")

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
        config = self.yaml.getEntries()
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
                    category = config["columns"]["NAME"]
                    if word in config[category]:
                        name += config[category][word]
                    else:
                        name += f" {word} "
                if len(name) == 0:
                    name = title.title()
                newname = str()
                if name.find(" Road") <= 0:
                    newname = f"{name} Road".replace('  ', ' ').strip()
                else:
                    newname = name.replace('  ', ' ').strip()
                # the < causes osmium to choke...
                props["name"] = newname.replace("<50", "&lt;50")

            # https://www.fs.usda.gov/Internet/FSE_DOCUMENTS/stelprd3793545.pdf
            if "OPER_MAINT_LEVEL" in entry["properties"] and entry["properties"]["OPER_MAINT_LEVEL"] is not None:
                field = entry["properties"]["OPER_MAINT_LEVEL"].split()[0]
                if field != "NA":
                    smoothness = config["tags"]["smoothness"][int(field)]
                    pair = smoothness.split('=')
                    props[pair[0]] = pair[1]

            if "PRIMARY_MAINTAINER" in entry["properties"] and  entry["properties"]["PRIMARY_MAINTAINER"] is not None:
                if entry["properties"]["PRIMARY_MAINTAINER"] == "FS - FOREST SERVICE":
                    props["operator"] = "US Forest Service"
                else:
                    props["operator"] = entry["properties"]["PRIMARY_MAINTAINER"].title()

            if "SURFACE_TYPE" in entry["properties"] and entry["properties"]["SURFACE_TYPE"]:
                if "surface" not in props:
                    # Only add a value for surface if it doesn't exist
                    field = entry["properties"]["SURFACE_TYPE"].split()[0]
                    if field in config["tags"]["surface"]:
                        surface = config["tags"]["surface"][field]
                        pair = surface.split('=')
                        props[pair[0]] = pair[1]

            if "SYMBOL_NAME" in entry["properties"] and entry["properties"]["SYMBOL_NAME"]:
                field = entry["properties"]["SYMBOL_NAME"][:4]
                symbol = config["tags"]["symbol"][field]
                pair = symbol.split('=')
                props[pair[0]] = pair[1]

            if "HIGH_CLEARANCE_VEHICLE" in entry["properties"]:
                if entry["properties"]["HIGH_CLEARANCE_VEHICLE"] is not None:
                    props["4wd_only"] = "yes"

            if "SEASONAL" in entry["properties"] and entry["properties"]["SEASONAL"]:
                seasonal = config["tags"]["seasonal"][entry["properties"]["SEASONAL"]]
                pair = seasonal.split('=')
                props[pair[0]] = pair[1]

            if geom is not None:
                props["highway"] = "unclassified"
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
    main()
