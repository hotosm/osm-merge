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
import asyncio
from codetiming import Timer
from time import sleep
from pathlib import Path
from progress.bar import Bar, PixelBar

# ogrmerge.py -single -o trails.shp VECTOR_*/Shape/Trans_TrailSegment.shp

# https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/
# Instantiate logger
log = logging.getLogger(__name__)

# https://wiki.openstreetmap.org/wiki/United_States_roads_tagging#Tagging_Forest_Roads

class USGS(object):
    def __init__(self,
                 filespec: str = None,
                 ):
        self.file = None
        if filespec is not None:
            self.file = open(filespec, "r")

    def convert(self,
                state: str,
                filespec: str = None,
                ) -> list:
        """
        Convert the USGS topographical dataset to something that can
        be conflated. The dataset schema is pretty ugly, duplicate
        field names, abbreviations, etc... plus a shapefile truncates
        the field names.

        Args:
            filespec (str): The input dataset file
            state (str): The 2 letter state abbreviation

        """
        # FIXME: read in the whole file for now
        if filespec is not None:
            file = open(filespec, "r")
        else:
            file = self.file

        data = geojson.load(file)

        highways = list()
        spin = Bar('Processing...', max=len(data['features']))
        for entry in data["features"]:
            geom = entry["geometry"]
            props = dict()
            spin.next()
            if "name" in entry["properties"]:
                props["name"] =  entry["properties"]["name"]
            if "sourceorig" in entry["properties"]:
                props["highway"] = "path"
                # These are for the trail data
                if entry['properties']['sourceorig'] is not None:
                    props["source"] = entry['properties']['sourceorig']
                if 'trailnumbe' in entry['properties']:
                    if entry['properties']['trailnumbe'] is not None:
                        props["ref:usfs"] = f"{entry['properties']['trailnumbe']}"
                if "bicycle" in entry['properties']:
                    if entry['properties']['bicycle'] is not None:
                        if entry['properties']['bicycle'] == "Y":
                            props["bicycle"] = "designated"
                        # else:
                        #     props["bicycle"] = "no"
                if "atv" in entry['properties']:
                    if entry['properties']['atv'] is not None:
                        if entry['properties']['atv'] == "Y":
                            props["atv"] = "designated"
                        # else:
                        #     props["atv"] = "no"
                if "packsaddle" in entry['properties']:
                    if entry['properties']['packsaddle'] is not None:
                        if entry['properties']['packsaddle'] == "Y":
                            props["horse"] = "designated"
                        # else:
                        #     props["horse"] = "no"
                if "motorcycle" in entry['properties']:
                    if entry['properties']['motorcycle'] is not None:
                        if entry['properties']['motorcycle'] == "Y":
                            props["motorcycle"] = "designated"
                        # else:
                        #     props["motorcycle"] = "no"
                if 'snowshoe' in entry['properties']:
                    if entry['properties']['snowshoe'] is not None:
                        if entry['properties']['snowshoe'] == "Y":
                            props["piste:type"] = "hike"
                    if entry['properties']['crosscount'] is not None:
                        if entry['properties']['crosscount'] == "Y":
                            props["ski"] = "yes"
                            props["piste:type"] = "nordic"
                # if entry['properties']['dogsled'] is not None:
                #     if entry['properties']['dogsled'] == "Y":
                #         props["dogsled"] = "yes"
                # if entry['properties']['hikerpedes'] is not None:
                #     if entry['properties']['hikerpedes'] == "Y":
                #         props["hiker"] = "yes"
                #     else:
                #         props["hiker"] = "no"
                if "snowmobile"in entry['properties']:
                    if entry['properties']['snowmobile'] is not None:
                        if entry['properties']['snowmobile'] == "Y":
                            props["snowmobile"] = "designated"
                        # else:
                        #     props["snowmobile"] = "no"
                if "motorizedw" in entry['properties']:
                    if entry['properties']['motorizedw'] is not None:
                        # FIXME: there's a better tag
                        if entry['properties']['motorizedw'] == "Y":
                            props["motorized"] = "designated"
                        # else:
                        #     props["motorized"] = "no"
                if len(props) == 0:
                    continue
                if geom is not None:
                    highways.append(Feature(geometry=geom, properties=props))
                continue
            
            # These are for the highways data
            if "highway" not in entry["properties"]:
                props["highway"] = "unclassified"
            if entry["properties"] is None or entry is None:
                continue
            if 'source_ori' in entry['properties']:
                if entry['properties']['source_ori'] is not None:
                    props["source"] = entry['properties']['source_ori']
            if 'us_route_a' in entry['properties']:
                if entry['properties']['us_route_a'] is not None:
                    props["ref"] = f"US {entry['properties']['us_route_a']}"
            if 'us_route' in entry['properties']:
                if entry['properties']['us_route'] is not None:
                    props["ref"] = f"US {entry['properties']['us_route']}"
            if 'county_rou' in entry['properties']:
                if entry['properties']['county_rou'] is not None:
                    props["ref"] = f"US {entry['properties']['county_rou']}"
            if 'state_ro_1' in entry['properties']:
                if entry['properties']['state_ro_1'] is not None:
                    props["ref"] = f"{state} {entry['properties']['state_ro_1']}"
            if 'state_rout' in entry['properties']:
                if entry['properties']['state_rout'] is not None:
                    props["ref"] = f"{state} {entry['properties']['state_rout']}"
            if 'federal_la' in entry['properties']:
                if entry['properties']['federal_la'] is not None:
                    # FIXME: add . between numbers and Letters.
                    props["ref:usfs"] = f"FR {entry['properties']['federal_la']}"

            if 'name' not in entry['properties']:
                continue
            if  entry['properties']['name'] is not None:
                if entry['properties']['name'][:8] == "USFS Rd ":
                    props["ref:usfs"] = f"FR {entry['properties']['name'][8:]}"
                elif entry['properties']['name'][:3] == "Rd ":
                    props["ref"] = f"CR {entry['properties']['name'][3:]}"
                    props["name"] = f"County Road {entry['properties']['name'][3:]}"
                elif entry['properties']['name'][:6] == "Co Rd ":
                    props["ref"] = f"CR {entry['properties']['name'][6:]}"
                    props["name"] = f"County Road {entry['properties']['name'][6:]}"
                elif entry['properties']['name'][:6] == "State Hwy ":
                    props["ref"] = f"{state} {entry['properties']['name'][6:]}"
                    props["name"] = f"State Highway {entry['properties']['name'][6:]}"
                elif entry['properties']['name'][:6] == "Us Hwy ":
                    props["ref"] = f"US {entry['properties']['name'][6:]}"
                    props["name"] = f"US Highway {entry['properties']['name'][6:]}"
                else:
                    # The USGS topo data when it comes to names is a real
                    # mess, full of abbreviations. So expand them which
                    # is what OSM prefers, and of course will be needed
                    # when conflating to get a string match.
                    name = f"{entry['properties']['name'].title()}"
                    name = name.replace(" Rd", " Road")
                    name = name.replace(" Hwy", " Highway")
                    name = name.replace(" Ln", " Lane")
                    name = name.replace(" Mnt", " Mountain ")
                    name = name.replace("E ", "East ")
                    name = name.replace("W ", "West ")
                    name = name.replace("N ", "North ")
                    name = name.replace("S ", "South ")
                    props["name"] = name

            if len(props) == 0 or geom is None:
                continue
            highways.append(Feature(geometry=geom, properties=props))

        return FeatureCollection(highways)

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="usgs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program converts USGS datasets into OSM tagging",
        epilog="""

    For Example: 
        mvum.py -v -c -i WY_RoadsMVUM.geojson
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Top-level input directory")
    parser.add_argument("-c", "--convert", default=True, action="store_true", help="Convert USGS feature to OSM feature")
    parser.add_argument("-s", "--state", default="CO", help="The state the dataset is in")
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

    usgs = USGS()
    if args.convert and args.convert:
        data = usgs.convert(args.state, args.infile)

        file = open(args.outfile, "w")
        geojson.dump(data, file, indent=4)
        log.info(f"Wrote {args.outfile}")
        
if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)
    # loop.run_until_complete(main())
    main()
