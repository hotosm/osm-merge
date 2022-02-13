#!/usr/bin/python3

#
# Copyright (C) 2022   Humanitarian OpenStreetMap Team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

# \file splitter.py split a large shapefile into smaller files
# after converting it to OSM XML format.

from osgeo import gdal,ogr,osr
# import shapely.wkt as wktlib
# from shapely.geometry import Polygon
import logging
from sys import argv
import getopt
from osmwriter import OsmFile

# default values for command line options
options = dict()
options['infile'] = None
options['outdir'] = "/tmp"
options['boundary'] = None

def usage(argv):
    out = """
    help(-h)     Get command line options
    verbose(-v)  Enable verbose output
    infile(-i)   Input data file in any OGR supported format OR
    database(-d) Input database to split
    project(-p)  Tasking Manager project ID to get boundaries
    outdir(-o)   Output directory for output files (default %s/tmp)
    boundary(-b) Specify a multipolygon as a boundaries, one file for each polygon
    """ % (options['outdir'])
    print(out)
    quit()

#if len(argv) <= 1:
if len(argv) < 1:
    usage(argv)

try:
    (opts, val) = getopt.getopt(argv[1:], "h,v,i:,o:,s:,b:",
        ["help", "verbose", "infile", "outdir", "size", "boundary"])
except getopt.GetoptError as e:
    logging.error('%r' % e)
    usage(argv)
    quit()
 
for (opt, val) in opts:
    if opt == '--help' or opt == '-h':
        usage(argv)
    elif opt == "--infile" or opt == '-i':
        options['infile'] = val
    elif opt == "--outdir" or opt == '-o':
        options['outdir'] = val
    elif opt == "--boundary" or opt == '-b':
        options['boundary'] = val
    

if options['infile'] is None and options['database']:
    logging.error("You need to specify an input file or database name!")
   
# Read file of any format
# filespec = "/play/MapData/Countries/Uganda/test.geojson"
# drv = ogr.GetDriverByName("GeoJSON")
# drv = ogr.GetDriverByName('ESRI Shapefile')
filespec = "/play/MapData/Countries/Uganda/Buildings Uganda GCC.shp"
infile = ogr.Open(filespec)
layer = infile.GetLayer()
featureCount = layer.GetFeatureCount()
print("Found %d" % featureCount)

osm = OsmFile(options)

for feature in layer:
    bld = dict()
    geom = feature.GetGeometryRef()
    bld['wkb'] = geom.ExportToWkt()
    bld['building'] = 'yes'
    txt = osm.createWay(bld)
    osm.writeOSM(txt)

osm.footer()
