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
from codetiming import Timer
from pathlib import Path
import re
from progress.spinner import Spinner
from osgeo import ogr
from codetiming import Timer
from osgeo import osr

# Instantiate logger
log = logging.getLogger(__name__)

def clip(boundary: str,
         infile: str,
         outfile: str,
         ):
    """
    Clip the data in a file by a multipolygon instead of using
    the command line program. The output file will only contain
    ways, in JOSM doing "File->update data' will load all the
    nodes so the highways are visible. It's slower of course
    than the C++ version, but this gives us better fine-grained
    control.

    Args:
        infile (str): The input data
        outfile (str): The output file
        boundary (str): The boundary

    Returns:
        (bool): Whether it worked or not
    """
    timer = Timer(text="clip() took {seconds:.0f}s")
    timer.start()

    driver = ogr.GetDriverByName('GeoJson')

    # The boundary file
    bounddata = driver.Open(boundary, 0)
    boundlayer = indata.GetLayer()

    # input file
    indata = driver.Open(infile, 0)
    inlayer = indata.GetLayer()
    if inlayer.GetFeatureCount() == 0:
        logging.error("Input Data is empty!!")
        return False

    # Output file
    if os.path.exists(outfile):
        os.remove(outfile)
    outdata = driver.CreateDataSource(outfile)
    outlayer = outdata.CreateLayer(task, geom_type=ogr.wkbLineString)

    defn = outlayer.GetLayerDefn()
    outfeat = ogr.Feature(defn)

    spin = Spinner('Processing boundaries...')

    # A boundary may contain multiple polygons
    for feature in inlayer:
        poly = feature.GetGeometryRef()
        outlayer.SetSpatialFilter(poly)
        for fineat in inlayer:
            outlayer.CreateFeature(infeat)
        


    timer.stop()
    return True

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="usgs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program extracts highways from MVUM",
        epilog="""
This program extracts all the highways from an MVUM file, and correct as
many of the bugs with names that are actually a reference number. 

    For Example: 
        mvumhighways.py -v -i colorado-latest.osm.pbf -o co-highways.osm
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Top-level input directory")
    parser.add_argument("-o", "--outfile", default="out.osm", help="Output file")
    parser.add_argument("-c", "--clip", help="Clip file by polygon")

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

    if args.clip:
        # cachefile = os.path.basename(args.infile.replace(".pbf", ".cache"))
        # create_nodecache(args.infile, cachefile)
        if not clip:
            log.error(f"You must specify a boundary!")
            parser.print_help()
            quit()
        if not args.infile:
            log.error(f"You must specify the input file!")
            parser.print_help()
            quit()

        clip(args.clip, args.infile, args.outfile)
        log.info(f"Wrote clipped file {args.outfile}")
        quit()

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
