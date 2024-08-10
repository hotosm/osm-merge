#!/bin/python3

# Copyright (c) 2022 Humanitarian OpenStreetMap Team
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
from pathlib import Path
# from tqdm import tqdm
# import tqdm.asyncio
import asyncio
from cpuinfo import get_cpu_info
from fmtm_splitter.splitter import split_by_square, FMTMSplitter
import geojson
import numpy as np
from geojson import Feature, FeatureCollection, GeoJSON
from shapely.geometry import Polygon, shape, LineString, MultiPolygon
# from shapely.geometry.geo import mapping
from cpuinfo import get_cpu_info
# import numpy as np
import shapely
# from shapely.prepared import prep
# from shapely.ops import split
# import pyproj
from functools import partial
from shapely.ops import transform
#import pyclipr
# import geopandas
from osgeo import ogr
import subprocess

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

# def grid_bounds(geom,
#                 delta: float,
#                 ):
    
#     minx, miny, maxx, maxy = geom.bounds
#     nx = int((maxx - minx)/delta)
#     ny = int((maxy - miny)/delta)
#     gx, gy = np.linspace(minx,maxx,nx), np.linspace(miny,maxy,ny)
#     grid = []
#     for i in range(len(gx)-1):
#         for j in range(len(gy)-1):
#             poly_ij = Polygon([[gx[i],gy[j]],[gx[i],gy[j+1]],[gx[i+1],gy[j+1]],[gx[i+1],gy[j]]])
#             grid.append( poly_ij )
#     return grid

# def partition(geom, delta):
#     prepared_geom = prep(geom)
#     grid = list(filter(prepared_geom.intersects, grid_bounds(geom, delta)))
#     return grid

# def geogrid(geom,
#             delta: float,
#             ):
#     """
#     """
#     xmin,ymin,xmax,ymax =  geom.total_bounds
#     width = 2000
#     height = 1000
#     rows = int(np.ceil((ymax-ymin) /  height))
#     cols = int(np.ceil((xmax-xmin) / width))
#     XleftOrigin = xmin
#     XrightOrigin = xmin + width
#     YtopOrigin = ymax
#     YbottomOrigin = ymax- height
#     polygons = []
#     for i in range(cols):
#         Ytop = YtopOrigin
#         Ybottom =YbottomOrigin
#         for j in range(rows):
#             polygons.append(Polygon([(XleftOrigin, Ytop), (XrightOrigin, Ytop), (XrightOrigin, Ybottom), (XleftOrigin, Ybottom)])) 
#             Ytop = Ytop - height
#             Ybottom = Ybottom - height
#         XleftOrigin = XleftOrigin + width
#         XrightOrigin = XrightOrigin + width

#     return gpd.GeoDataFrame({'geometry':polygons})

# def splitPolygon(polygon,
#                  nx,
#                  ny):
#     """
#     Split a polygons into stask quares.

#     Args:

#     Returns:
    
#     """
#     minx, miny, maxx, maxy = polygon.bounds
#     dx = (maxx - minx) / nx
#     dy = (maxy - miny) / ny

#     minx, miny, maxx, maxy = polygon.bounds
#     dx = (maxx - minx) / nx  # width of a small part
#     dy = (maxy - miny) / ny  # height of a small part
#     horizontal_splitters = [LineString([(minx, miny + i*dy), (maxx, miny + i*dy)]) for i in range(ny)]
#     vertical_splitters = [LineString([(minx + i*dx, miny), (minx + i*dx, maxy)]) for i in range(nx)]
#     splitters = horizontal_splitters + vertical_splitters
#     result = polygon
    
#     for splitter in splitters:
#         result = MultiPolygon(split(result, splitter))
    
#     return result

async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program extracts boundaries from USDA datasets",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="verbose output")
    parser.add_argument("-i", "--infile", required=True,
                        help="The input dataset")
    parser.add_argument("-g", "--grid", action="store_true",
                        help="Generate the task grid")
    parser.add_argument("-s", "--split", action="store_true",
                        help="Split Multipolygon")
    parser.add_argument("-o", "--outfile", default="output.geojson",
                        help="Output filename")
    parser.add_argument("-e", "--extract", help="Split Dataset with Multipolygon")
    parser.add_argument("-t", "--threshold", default=0.5,
                        help="Threshold")
    # parser.add_argument("-s", "--size", help="Grid size in kilometers")

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


    # The infile is either the the file to split, or the grid file.
    file = open(args.infile, "r")
    grid = geojson.load(file)
    
    # Split the large file of administrative boundaries into each
    # area so they can be used for clipping.
    if args.split:
        index = 0
        name = str()
        for feature in data['features']:
            if "FORESTNAME" in feature["properties"]:
                name = feature["properties"]["FORESTNAME"].replace(' ', '_')
            else:
                name = f"{path.stem}_{index}"
                index += 1
                feature["properties"]["name"] = name
                feature["boundary"] = "administrative"
            file = open(f"{name}.geojson", 'w')
            geojson.dump(FeatureCollection([feature]), file)
            file.close()
    elif args.grid:
        log.info(f"Generating the grid may take a long time...")
        grid = split_by_square(grid, meters=50000, outfile=args.outfile)
        log.info(f"Wrote {args.outfile}")
    if args.extract:
        # Split a data extract into task sized chunks.
        # file = open(args.extract, "r")
        # data = geojson.load(file)
        # log.debug(f"Input File has {len(grid["features"])} features")
        # log.debug(f"Extract File has {len(data["features"])} features")
        # for task in grid["features"]:
        #     log.debug(f"{task["properties"]}")
        #     taskgeom = shape(task["geometry"])
        #     for feature in data["features"]:
        #         if feature["geometry"] is None:
        #             continue
        #         entry = shape(feature["geometry"])
        #         if taskgeom.intersects(entry):
        #             log.debug(f"Intersects! {feature["properties"]}")
        #             break
        #         if shapely.contains(taskgeom, entry):
        #             log.debug(f"Contains! {feature["properties"]}")
        #             break
        # for task in data:
        #     result = subprocess.run([
        #         "ogr2ogr",
        #         "--overwrite",
        #         "--clipsrc",
                   
        #         f"{infile}",
        #         ]
        #     )

        driver = ogr.GetDriverByName("GeoJson")
        indata = driver.Open(args.infile, 0)
        inlayer = indata.GetLayer()
        indefn = inlayer.GetLayerDefn()
        logging.debug(f"Input File{inlayer.GetFeatureCount()} features before filtering")

        extdata = driver.Open(args.extract, 0)
        extlayer = extdata.GetLayer()
        extdefn = extlayer.GetLayerDefn()
        logging.debug(f"External dataset {extlayer.GetFeatureCount()} features before filtering")

        index = 0
        path = Path(args.outfile)
        for task in inlayer:
            extlayer.SetSpatialFilter(task.GetGeometryRef())
            if extlayer.GetFeatureCount() == 0:
                # logging.debug("Data is empty!!")
                continue
            outdata = driver.CreateDataSource(f"{path.stem}_{index}.geojson")
            outlayer = outdata.CreateLayer("test", geom_type=ogr.wkbMultiLineString)
            for feature in extlayer:
                outlayer.CreateFeature(feature)
            #outlayer.Destroy()
            
            index += 1

        # for feature in inlayer:
        #     # g = inlayer.GetGeometryRef(i)
        #     # print(feature.ExportToJson())
        #     # geom = feature.GetGeometryRef()
        #     # geom2 = extlayer.GetGeometryRef()
        # ogr.Layer.Clip(inlayer, extlayer, outlayer)
        #feature.Destroy()
        
        # tasks = geopandas.read_file(args.infile)
        # tasks.to_crs(epsg=3857)
        # extract = geopandas.read_file(args.extract)
        # extract.to_crs(epsg=3857)
        # for task in tasks.iterfeatures():
        #     foo = extract.clip(task)
        # le = open(args.infile, "r")
        # extdata = geojson.load(file)
        #for feature in grid["features"]:
            # po.addPaths([shapely.get_coordinates(grid)], pyclipr.JoinType.Miter, pyclipr.EndType.Polygon)
            # offsetSquare = po.execute(10.0)
            # pc = pyclipr.Clipper()
            # pc.scaleFactor = int(1000)
            # pc.addPaths(offsetSquare, pyclipr.Subject)
            # pc.addPath(shapely.get_coordinates(shapely.get_coordinates(boundary)), pyclipr.Clip)
            # out  = pc.execute(pyclipr.Intersection, pyclipr.FillRule.EvenOdd)
            # out2 = pc.execute(pyclipr.Union, pyclipr.FillRule.EvenOdd)
            # out3 = pc.execute(pyclipr.Difference, pyclipr.FillRule.EvenOdd)
            # out4 = pc.execute(pyclipr.Xor, pyclipr.FillRule.EvenOdd)
            # print(out)

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
