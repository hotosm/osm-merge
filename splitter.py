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

from osgeo import ogr
import shapely.wkt as wktlib
import logging
from sys import argv
import getopt
import os
from progress.spinner import PixelSpinner


# Process command line arguments
try:
    (opts, val) = getopt.getopt(argv[1:], "h,v,i:,d:,p:,o:,b:",
        ["help", "verbose", "infile", "database", "project", "outdir", "boundary"])
except getopt.GetoptError as e:
    logging.error('%r' % e)
    usage(argv)
    quit()
 
# default values for command line options
options = dict()
options['infile'] = None
options['database'] = None
options['project'] = None
options['boundary'] = None
options['outdir'] = "/tmp"

def writeData(file = None, buildings = None):
    if file is None:
        logging.error("Supply a filespec!")
        return
    if buildings.GetFeatureCount() == 0:
        logging.error("Building data is empty!!")
        return

    # drv = ogr.GetDriverByName('ESRI Shapefile')
    drv = ogr.GetDriverByName("GeoJSON")
    # Delete the output file if it exists
    if os.path.exists(file):
        drv.DeleteDataSource(file)

    outfile  = drv.CreateDataSource(file)
    layer = outfile.CreateLayer("footprints", geom_type=ogr.wkbPolygon)

    # spin = PixelSpinner('Processing...')
    import epdb; epdb.st()
    for poly in buildings:
        # spin.next()
        layer.CreateFeature(poly)

    outfile.Destroy()

def usage(argv):
    out = """
    --help(-h)     Get command line options
    --verbose(-v)  Enable verbose output
    --infile(-i)   Input data file in any OGR supported format OR
    --database(-d) Input database to split
    --project(-p)  Tasking Manager project ID to get boundaries
    --outdir(-o)   Output directory for output files (default \"%s\")
    --boundary(-b) Specify a multipolygon as a boundaries, one file for each polygon
    """ % (options['outdir'])
    print(out)
    quit()

if len(argv) <= 1:
    usage(argv)

for (opt, val) in opts:
    if opt == '--help' or opt == '-h':
        usage(argv)
    elif opt == "--infile" or opt == '-i':
        options['infile'] = val
    elif opt == "--outdir" or opt == '-o':
        options['outdir'] = val
    elif opt == "--project" or opt == '-p':
        options['project'] = val
    elif opt == "--database" or opt == '-d':
        options['database'] = val
    elif opt == "--boundary" or opt == '-b':
        options['boundary'] = val
    

if options['infile'] is None and options['database'] is None:
    logging.error("You need to specify an input file or database name!")
    usage(argv)
   
# Read file of any format
# filespec = "/play/MapData/Countries/Uganda/test.geojson"

project_boundary = ogr.Geometry(ogr.wkbPolygon)
task_boundary = ogr.Geometry(ogr.wkbPolygon)

# The boundary is a multipolygon, usually a Tasking Manager project boundary,
# or all the task boundaries in thie project. It has one layer which is
# called sql_statement.
project_id = None
if options['boundary'] is not None:
    logging.info("Opening boundary file %s" % options['boundary'])
    bounds = ogr.Open(options['boundary'])
    blayer = bounds.GetLayer("tmproject")
    print("%d Boundaries in %s" % (blayer.GetFeatureCount(), options['boundary']))
    layerdef = blayer.GetLayerDefn()
    print("Field Count: %d" % layerdef.GetFieldCount())
    # for i in range(layerdef.GetFieldCount()):
    #     print(layerdef.GetFieldDefn(i).GetName())
    project_id = blayer.GetFeature(0).GetField(0)

    feature = blayer.GetFeature(0)
    project_boundary = feature.GetGeometryRef()

    # The input file is GeoJson format, and has one layer, which is the name of the country.
    # It consiste of only polygons of building footprints.
    logging.info("Opening footprints file %s, please wait..." % options['infile'])
    infile = ogr.Open(options['infile'])
    layer = infile.GetLayer()

    # Create a Polygon from the extent tuple
    ring = ogr.Geometry(ogr.wkbLinearRing)
    extent = blayer.GetExtent()
    ring.AddPoint(extent[0],extent[2])
    ring.AddPoint(extent[1], extent[2])
    ring.AddPoint(extent[1], extent[3])
    ring.AddPoint(extent[0], extent[3])
    ring.AddPoint(extent[0],extent[2])
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)
    print("%d features in %s" % (layer.GetFeatureCount(), options['infile']))

    print("Extracting features within the boundary, please wait...")
    layer.SetSpatialFilter(poly)

    # wkt = "POLYGON ((20.08484443554 5.28903721725,20.26867520555 5.28903721725,20.26867520555 5.43783487479,20.08484443554 5.43783487479,20.08484443554 5.28903721725))"
    # layer.SetSpatialFilter(ogr.CreateGeometryFromWkt(wkt))

    print("%d features in %s after filtering" % (layer.GetFeatureCount(), options['infile']))
    if (layerdef.GetFieldCount() == 1):
        writeData("tmproject-" + str(project_id) + ".geojson", layer)
    else:
        i = 0
        feature = layer.GetNextFeature()
        while feature is not None:
            if project_boundary.Within(feature.GetGeometryRef()):
                print("Is in boundary!")
            else:
                print("Is not in boundary!")
            task_id = feature.GetField(1)
            geom = feature.GetGeometryRef()
            writeData("tmproject-" + str(project_id) + "--task-" + task_id + ".geojson", layer)
            feature = None
            i += 1
        print("%d features in %s after filtering" % (i, options['infile']))
