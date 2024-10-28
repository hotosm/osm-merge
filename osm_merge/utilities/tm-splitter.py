#!/bin/python3

# Copyright (c) 2024 OpenStreetMap US
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     FMTM-Splitter is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with FMTM-Splitter.  If not, see <https:#www.gnu.org/licenses/>.
#


"""
Class and helper methods for task splitting when working with the HOT
Tasking Manager since our projects are larger than 5000km area it
supports.
"""

import argparse
import json
import logging
import sys
import os
from math import ceil

from pathlib import Path
# from tqdm import tqdm
# import tqdm.asyncio
import asyncio
from cpuinfo import get_cpu_info
import geojson
import numpy as np
from geojson import Feature, FeatureCollection, GeoJSON
from shapely.geometry import Polygon, shape, LineString, MultiPolygon
from shapely.prepared import prep
from shapely.ops import split
from cpuinfo import get_cpu_info
import shapely
from functools import partial
from shapely.ops import transform
from osgeo import ogr
from codetiming import Timer
from osgeo import osr
from progress.spinner import Spinner

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

def ogrgrid(outputGridfn: str,
            extent: tuple,
            threshold: float,
            # outLayer: ogr.Layer,
            ):
    """
    Generate a task grid.
    https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-fishnet-grid
    
    """
    # timer = Timer(text="ogrgrid() took {seconds:.0f}s")
    # timer.start()

    # convert sys.argv to float
    xmin = extent[0]
    xmax = extent[1]
    ymin = extent[2]
    ymax = extent[3]
    gridWidth = float(threshold)
    gridHeight = gridWidth
    # get rows
    rows = ceil((ymax-ymin)/gridHeight)
    # get columns
    cols = ceil((xmax-xmin)/gridWidth)

    # start grid cell envelope
    ringXleftOrigin = xmin
    ringXrightOrigin = xmin + gridWidth
    ringYtopOrigin = ymax
    ringYbottomOrigin = ymax-gridHeight

    # create output file
    outDriver = ogr.GetDriverByName('GeoJson')
    if os.path.exists(outputGridfn):
        os.remove(outputGridfn)
    outDataSource = outDriver.CreateDataSource(outputGridfn)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    outLayer = outDataSource.CreateLayer(outputGridfn, srs, geom_type=ogr.wkbMultiPolygon )
    featureDefn = outLayer.GetLayerDefn()
    name = ogr.FieldDefn("name", ogr.OFTString)
    outLayer.CreateField(name)

    # create grid cells
    countcols = 0
    index = 0
    while countcols < cols:
        countcols += 1

        # reset envelope for rows
        ringYtop = ringYtopOrigin
        ringYbottom =ringYbottomOrigin
        countrows = 0

        while countrows < rows:
            countrows += 1
            ring = ogr.Geometry(ogr.wkbLinearRing)
            ring.AddPoint(ringXleftOrigin, ringYtop)
            ring.AddPoint(ringXrightOrigin, ringYtop)
            ring.AddPoint(ringXrightOrigin, ringYbottom)
            ring.AddPoint(ringXleftOrigin, ringYbottom)
            ring.AddPoint(ringXleftOrigin, ringYtop)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)

            # add new geom to layer
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(poly)
            outFeature.SetField("name", f"Task_{countrows}_{countcols}")
            outLayer.CreateFeature(outFeature)

            # new envelope for next poly
            ringYtop = ringYtop - gridHeight
            ringYbottom = ringYbottom - gridHeight

            index += 1

        # new envelope for next poly
        ringXleftOrigin = ringXleftOrigin + gridWidth
        ringXrightOrigin = ringXrightOrigin + gridWidth

    # Save and close DataSources
    outDataSource = None

    # timer.stop()
    return outLayer

def make_extract(infile: str,
                 boundary: str,
                 complete: bool,
               ):
    """
    Make the data extracts, one for each polygon in the input file. This
    assumes the data has already been tag filtered, and just needs to
    be split into task sized chunks.

    By default, all linestrings are clipped to the boundary. The complete
    option is slower, but linestrings that cross the boundary are completed
    to the extent they are in the input file. This mimics the behaviour of
    both osmium and osmconvert.

    Args:
        infile (str): The filespec of the input file.
        boundary (str): The filespec of the boundary mutlipolygon file.
        complete (bool): Whether to complete linestrings outside the boundary.
    """
    index = 0
    name = str()
    driver = ogr.GetDriverByName("GeoJson")
    indata = driver.Open(infile, 0)
    inlayer = indata.GetLayer()
    logging.debug(f"There are {inlayer.GetFeatureCount()} in the boundary dataset")

    # The task boundaries
    bounddata = driver.Open(boundary, 0)
    boundlayer = bounddata.GetLayer()
    bounddefn = boundlayer.GetLayerDefn()
    logging.debug(f"There are {boundlayer.GetFeatureCount()} in the boundary dataset")
    spin = Spinner('Processing features ...')

    for feature in boundlayer:
        name = "foo" # feature.GetField(0)
        # There's only one field in the grid multipolygon, the name,
        # which includes the task number.
        outfile = f"{name}-tmp.geojson"
        if os.path.exists(outfile):
            os.remove(outfile)
        outdata = driver.CreateDataSource(outfile)
        outlayer = outdata.CreateLayer("highways", geom_type=ogr.wkbLineString)
        defn = outlayer.GetLayerDefn()
        outfeat = ogr.Feature(defn)
        poly = feature.GetGeometryRef()
        if not complete:
            inlayer.SetSpatialFilter(poly)
        else:
            for infeat in inlayer:
                spin.next()
                test = infeat.GetGeometryRef()
                if poly.Intersects(test) or poly.Contains(test):
                    # log.debug(f"In boundary for {infeat}")
                    # simple = test.Simplify(2.0)
                    outlayer.CreateFeature(infeat)
            # continue
        # outFeature.SetGeometry(poly)
        # name = ogr.FieldDefn("name", ogr.OFTString)
        # # outlayer.CreateField(name)
        # # outFeature.SetField("name", outfile)
        # # feature["properties"]["name"] = name
        # # feature["boundary"] = "administrative"
        logging.debug(f"There are {outlayer.GetFeatureCount()} in the output dataset")
        outdata.Destroy()
        log.debug(f"Wrote task {outfile} ...")

def make_tasks(infile: str,
               outfile: str,
               ):
    """
    Make the task files, one for each polygon in the input file.

    Args:
        infile (str): The filespec of the input file.
        outfile (str): Template for the output files
    """
    index = 0
    name = str()
    driver = ogr.GetDriverByName("GeoJson")
    indata = driver.Open(infile, 0)
    inlayer = indata.GetLayer()
    for feature in inlayer:
        # This is only in the USDA administrative boundaries file.
        # for feature in inlayer:
        # if "FORESTNAME" in feature["properties"]:
        #     name = feature["properties"]["FORESTNAME"].replace(' ', '_')
        # elif "UNIT_NAME" in feature["properties"]:
        #     name = feature["properties"]["UNIT_NAME"].replace(' ', '_').replace('/', '_')

        # There's only one field in the grid multipolygon, the task number.
        # FIXME: it turns out there may be multipolygons, so they all wind
        # up with the same task name, so use an index here instead.
        # task = feature.GetField(0)
        taskfile = f"{outfile}_Task_{index}.geojson"
        index += 1
        task = Path(taskfile).stem.replace("Tasks", "Task")
        if os.path.exists(taskfile):
            os.remove(taskfile)
        outdata = driver.CreateDataSource(taskfile)
        outlayer = outdata.CreateLayer(task, geom_type=ogr.wkbMultiPolygon)
        featureDefn = outlayer.GetLayerDefn()
        outFeature = ogr.Feature(featureDefn)
        poly = feature.GetGeometryRef()
        # Make a polygon if it's closed, which it should be. Using ogr2ogr to
        # clip the grid to the boundary, it sets some task as a LineString
        # instead of a polygon. Since the first and last points are the same,
        # it's actually a polygon, so convert it to a Polygon.
        if poly.GetGeometryName() == "LINESTRING":
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for i in range(0, poly.GetPointCount()):
                pt = poly.GetPoint(i)
                ring.AddPoint(pt[0], pt[1])
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)
        outFeature.SetGeometry(poly)
        name = ogr.FieldDefn("name", ogr.OFTString)
        # outlayer.CreateField(name)
        # outFeature.SetField("name", outfile)
        outlayer.CreateFeature(outFeature)
        # feature["properties"]["name"] = name
        # feature["boundary"] = "administrative"
        log.debug(f"Wrote task {taskfile} ...")

async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="tm-splitter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program manages tasks splitting",
        epilog="""
        This program implements some HOT Tasking Manager style functions
for use in other programs. This can generate a grid of tasks from an
AOI, and it can also split the multipolygon of that grid into seperate
files to use for clipping with ogr2ogr.

To break up a large public land boundary, a threshold of 0.7 gives
us a grid of just under 5000 sq km, which is the TM limit.

	tm-splitter.py --grid --infile boundary.geojson --threshold 0.7

To split the grid file file into tasks, this will generate a separate
file for each polygon within the grid. This file can then also be used
for clipping with other tools like ogr2ogr, osmium, or osmconvert.

	tm-splitter.py --split --infile tasks.geojson


	tm-splitter.py --split --infile tasks.geojson

This will split the data extract into a task sized chunk, one for each
polygon in the boundary file. All linestrings are completed to avoid
problems with conflation.

        /tm-splitter.py -v --complete -i infile.geojson -e boundary.geojson
"""
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="verbose output")
    parser.add_argument("-i", "--infile", required=True,
                        help="The input dataset")
    parser.add_argument("-g", "--grid", action="store_true",
                        help="Generate the task grid")
    parser.add_argument("-s", "--split", default=False, action="store_true",
                        help="Split Multipolygon")
    parser.add_argument("-o", "--outfile", default="output.geojson",
                        help="Output filename")
    parser.add_argument("-e", "--extract", default=False, help="Split Dataset with Multipolygon")
    parser.add_argument("-c", "--complete",  action="store_true", help="Complete all LineStrings")
    parser.add_argument("-t", "--threshold", default=0.1,
                        help="Threshold")
    # parser.add_argument("-s", "--size", help="Grid size in kilometers")

    args = parser.parse_args()
    indata = None
    source = None
    path = Path(args.infile)

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

    # The infile is either the the file to split, or the grid file.
    if not os.path.exists(args.infile):
        log.error(f"{args.infile} does not exist!")
        quit()

    file = open(args.infile, "r")
    grid = geojson.load(file)
    
    # Split the large file of administrative boundaries into each
    # area so they can be used for clipping.
    if args.split:
        make_tasks(args.infile, args.outfile)
    elif args.grid:
        log.debug(f"Generating the grid may take a long time...")
        path = Path(args.outfile)
        #grid2 = partition(grid, float(1.1))
        driver = ogr.GetDriverByName("GeoJson")
        indata = driver.Open(args.infile, 0)
        inlayer = indata.GetLayer()
        crs = inlayer.GetSpatialRef()
        extent = inlayer.GetExtent()

        memdrv = ogr.GetDriverByName("Memory")
        memdata = memdrv.CreateDataSource(f"mem")
        # memlayer = memdata.CreateLayer("tasks", geom_type=ogr.wkbPolygon)
        out = ogrgrid(args.outfile, extent, args.threshold)
        fodata = driver.Open("bar.geojson", 0)
        folayer = indata.GetLayer()
        outfile = f"{path.stem}_grid.geojson"
        outdata = driver.CreateDataSource(outfile)
        if os.path.exists(outfile):
            os.remove(outfile)
        outlayer = outdata.CreateLayer("Tasks", crs, geom_type=ogr.wkbPolygon)

        boundary = inlayer.GetNextFeature()
        if not boundary:
            log.error(f"The boundary file {args.infile} is empty")
            quit()

        poly = boundary.GetGeometryRef()

        index = 0
        # 1 meters is this factor in degrees
        # meter = 0.0000114

        log.debug(f"Wrote {args.outfile}")

    if args.extract:
        # Use gdal, as it was actually easier than geopandas or pyclir
        make_extract(args.infile, args.extract, args.complete)

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
