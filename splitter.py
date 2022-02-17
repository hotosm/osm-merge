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
    (opts, val) = getopt.getopt(argv[1:], "h,v,i:,d:,p:,o:,b:,t:,s",
        ["help", "verbose", "infile", "database", "project", "outdir", "boundary", "tmdatabase", "splittask"])
except getopt.GetoptError as e:
    logging.error('%r' % e)
    usage(argv)
    quit()
 
# default values for command line options
options = dict()
options['tasks'] = False
options['infile'] = None
options['tmdb'] = None
options['buildings'] = None
options['project'] = None
options['boundary'] = None
options['outdir'] = "/tmp"
project_id = None

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
    for poly in buildings:
        # spin.next()
        layer.CreateFeature(poly)

    outfile.Destroy()

def usage(argv):
    out = """
    --help(-h)     Get command line options
    --verbose(-v)  Enable verbose output
    --infile(-i)   Input data file in any OGR supported format OR
    --tmdatabase(-t) Tasking Manager database to split
    --splittasks(-s) When using the Tasking Manager database, split into tasks
    --buildings(-b) Building footprint database to split
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
    elif opt == "--splittask" or opt == '-s':
        options['tasks'] = True
    elif opt == "--outdir" or opt == '-o':
        options['outdir'] = val
    elif opt == "--project" or opt == '-p':
        options['project'] = val
    elif opt == "--tmdatabase" or opt == '-t':
        options['tmdb'] = val
    elif opt == "--tmdatabase" or opt == '-t':
        options['buildings'] = val
    elif opt == "--rmdatabase" or opt == '-t':
        options['tmdb'] = val
    elif opt == "--boundary" or opt == '-b':
        options['boundary'] = val
    

if options['infile'] is None and options['buildings'] is None:
    logging.error("You need to specify an input file or database name!")
    usage(argv)
   
project_boundary = ogr.Geometry(ogr.wkbPolygon)
task_boundary = ogr.Geometry(ogr.wkbPolygon)

# The boundary is a multipolygon, usually a Tasking Manager project boundary,
# or all the task boundaries in thie project. It has one layer which is
# called tmproject.
if options['tmdb'] is not None:
    # dburl = "PG: host=%s dbname=%s user=%s password=%s" % (databaseServer,databaseName,databaseUser,databasePW)
    dburl = "PG: dbname=tmsnap"
    bounds = ogr.Open(dburl)
    if options['tasks']:
        sql = "SELECT projects.id AS pid,tasks.id AS tid,ST_AsText(tasks.geometry) FROM tasks,projects WHERE tasks.project_id=" + str(options['project']) + " AND projects.id=" + str(options['project'])
    else:
        sql = "SELECT id AS pid,ST_AsText(geometry) FROM projects WHERE id=" + str(options['project'])
    print(sql)
    blayer = bounds.ExecuteSQL(sql)
    project_id = options['project']
    # import epdb; epdb.st()

if options['boundary'] is not None:
    logging.info("Opening boundary file %s" % options['boundary'])
    bounds = ogr.Open(options['boundary'])
    blayer = bounds.GetLayer("tmproject")
    print("%d Boundaries in %s" % (blayer.GetFeatureCount(), options['boundary']))
    project_id = blayer.GetFeature(0).GetField(0)

layerdef = blayer.GetLayerDefn()
print("Field Count: %d" % layerdef.GetFieldCount())

feature = blayer.GetFeature(0)
project_boundary = feature.GetGeometryRef()

# The input file is GeoJson format, and has one layer, which is the name of the country.
# It consists of only polygons of building footprints.
logging.info("Opening footprints file %s, please wait..." % options['infile'])

infile = ogr.Open(options['infile'])
layer = infile.GetLayer()

# Create a bounding box. since we want a rectangular area to extract to fit a monitor window
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

if (layerdef.GetFieldCount() == 1):
    print("Extracting features within the boundary, please wait...")
    layer.SetSpatialFilter(poly)
    print("%d features in %s after filtering" % (layer.GetFeatureCount(), options['infile']))
    writeData("tmproject-" + str(project_id) + ".geojson", layer)
else:
    i = 0
    feature = layer.GetNextFeature()
    for feature in blayer:
        task_id = feature.GetField(1)
        task_boundary = feature.GetGeometryRef()
        print("Extracting features within the boundary, please wait...")
        layer.SetSpatialFilter(task_boundary)
        print("%d features in %s after filtering" % (layer.GetFeatureCount(), options['infile']))
        if layer.GetFeatureCount() > 0:
            writeData("tmproject-" + str(project_id) + "-task-" + str(task_id) + ".geojson", layer)
