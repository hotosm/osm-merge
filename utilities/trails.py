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

        highways = list()
        for entry in data["features"]:
            geom = entry["geometry"]
            id = 0
            sym = 0
            op = None
            surface = str()
            name = str()
            props = dict()
            # These are the defaults for all trail features
            props["highway"] = "path"
            props["operator"] = "National Forest Service"
            props["access"] = "public"
            props["informal"] = "no"
            # print(entry["properties"])
            for key, value in entry["properties"].items():
                if value == "N/A" or value is None:
                    continue
                # print(key, value)
                if key == "TRAIL_NO":
                    props["ref:usfs"] = f"FR {value}"
                if key == "TRAIL_NAME":
                    props["name"] = value.title()
                if key == "SNOWMOBILE_ACCPT" or key == "SNOWMOBILE_MANAGED":
                    props["snowmobile"] = "yes"
                if key == key == "SNOWMOBILE_RESTRICTED":
                    props["snowmobile"] = "no"
                if key == "HIKER_PEDESTRIAN_MANAGED" or key == "HIKER_PEDESTRIAN_ACCPT":
                    props["access"] = "public"
                if key == "BICYCLE_MANAGED" or key == "_BICYCLEACCPT":
                    props["bicycle"] = "yes"
                if key == "BICYCLE_RESTRICTED":
                    props["bicycle"] = "no"
                if key == "ATV_MANAGED" or key == "ATV_ACCPT":
                    props["atv"] = "yes"
                if key == "ATV_RESTRICTED":
                    props["atv"] = "no"
                if key == "MOTORCYCLE_MANAGED" or key == "MOTORCYCLE_ACCPT":
                    props["motorcycle"] = "yes"
                if key == "MOTORCYCLE_RESTRICTED":
                    props["motorcycle"] = "no"
                if key == "PACK_SADDLE_MANAGED" or key == "PACK_SADDLE_ACCPT:":
                    props["horse"] = "yes"
                if key == "PACK_SADDLE_RESTRICTED":
                    props["horse"] = "no"
                if key == "SNOWSHOE_MANAGED" or key == "SNOWSHOE_ACCPT":
                    props["snowshoe"] = "yes"
                if key == "SNOWSHOE_RESTRICTED":
                    props["snowshoe"] = "no"
                if key == "XCOUNTRY_SKI_MANAGED" or key == "XCOUNTRY_SKI_ACCPT":
                    props["ski"] = "yes"
                if key == "XCOUNTRY_SKI_RESTRICTED":
                    props["ski"] = "no"

            if geom is not None:
                highways.append(Feature(geometry=geom, properties=props))
            #print(props)

        return FeatureCollection(highways)
        
    
async def main():
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

    mvum = MVUM()
    if args.convert and args.convert:
        data = mvum.convert(args.infile)

        file = open(args.outfile, "w")
        geojson.dump(data, file)
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
