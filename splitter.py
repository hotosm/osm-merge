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
import sys
import epdb
from progress.spinner import PixelSpinner
import hotstuff


# Process command line arguments
# default values for command line options

# All command line options
options = hotstuff.CommonOptions(argv)

project_id = None

def usage(argv):
    out = """
    --help(-h)       Get command line options
    --verbose(-v)    Enable verbose output
    --boundary(-b)   Specify a multipolygon for boundaries, one file for each polygon
    --tmin(-t)       Tasking Manager database to get boundaries
    --project(-p)    Tasking Manager project ID to get boundaries from database
    --splittasks(-s) When using the Tasking Manager database, split into tasks
    --osmin(-x)      OSM XML or OSM database to get boundaries
    --admin(-a)      When using the OSM database, this is the admin_level
    --data(-d)       Data source to split
    --outdir(-o)     Output directory for output files (default \"%s\")

    Since the data files are huge, a boundary is used to extract a subset of the data.
    This can be from the Tasking Manager database, administrative boundaries in
    an OSM database, or a disk file. One output file for each polygon in the boundary
    is created.

    Examples:
    The command: splitter.py -b 8345-project.geojson -i kenya.geojsonl
    creates *tmproject-8345.geojson*

    The command:  splitter.py -b 8345-tasks.geojson -i kenya.geojsonl
    creates *tmproject-8345-task-[0-9]+.geojson*

    The command: splitter.py -p 8345 -t tmsnap -i kenya.geojsonl
    creates *tmproject-8345.geojson*, by getting the boundary from a database

    The command:
    splitter.py -p 8345 -t tmsnap -s -i kenya.geojsonl
    creates *tmproject-8345-task-[0-9]+.geojson*, by getting the task boundaries from a database

    """ % (options['prefix'])
    print(out)
    quit()

# if len(argv) <= 1:
#     usage(argv)

# try:
#     (opts, val) = getopt.getopt(argv[1:], "h,v,b:,t:,p:,s,x:,a:,d:,o:",
#                                 ["help", "verbose", "boundary", "tmin", "project", "splittask", "osmin", "admin_level", "data", "outdir"])
# except getopt.GetoptError as e:
#     logging.error('%r' % e)
#     usage(argv)
#     quit()

# for (opt, val) in opts:
#     if opt == '--help' or opt == '-h':
#         usage(argv)
#     elif opt == "--osmin" or opt == '-x':
#         options['osmin'] = val
#     elif opt == "--verbose" or opt == '-v':
#         # logging.basicConfig(filename='splitter.log',level=logging.DEBUG)
#         logging.basicConfig(stream = sys.stdout,level=logging.DEBUG)
#     elif opt == "--splittask" or opt == '-s':
#         options['tasks'] = True
#     elif opt == "--outdir" or opt == '-o':
#         options['outdir'] = val
#     elif opt == "--project" or opt == '-p':
#         options['project'] = val
#     elif opt == "--data" or opt == '-d':
#         options['data'] = val
#     elif opt == "--tmin" or opt == '-t':
#         options['tmin'] = val
#     elif opt == "--admin" or opt == '-a':
#         options['admin'] = val
#     elif opt == "--boundary" or opt == '-b':
#         options['boundary'] = val

# if options['tmin'] is None and options['data'] is None:
#     logging.error("You need to specify an input file or database name!")
#     usage(argv)
   
# project_boundary = ogr.Geometry(ogr.wkbPolygon)

# All command line options
options = hotstuff.CommonOptions(argv)

dbhost = options.get('dbhost')

# Boundary file of polygons
row = hotstuff.getProjectBoundary(options)
if row is None:
    logging.error("Unable to get boundary from %s" % options['boundary'])
    quit()

# The input file or database for the data to split
if options.get('footprints'):
    data = options.get('footprints')
    if data[0:3] == "pg:":
        logging.info("Opening database %s, please wait..." % data[3:])
        connect = "PG: dbname=" + data[3:]
        if dbhost != "localhost":
            connect += " host=" + dbhost
        tmp = ogr.Open(connect)
    else:
        logging.info("Opening data file %s, please wait..." % data)
        tmp = ogr.Open(data)
    layer = tmp.GetLayer()
    logging.debug("%d features in %s" % (layer.GetFeatureCount(), data))

logging.info("Extracting features within the boundary, please wait...")

index = 0
for poly in row:
    layer.ResetReading()
    logging.debug("%d features before filtering" % layer.GetFeatureCount())
    layer.SetSpatialFilter(poly['boundary'])
    logging.error("%d features after filtering" % layer.GetFeatureCount())
    if options.get('project') is not None and layer.GetFeatureCount() > 0:
        out = options['outdir'] + str(options.get('project')) + ".geojson"
        logging.info("Writing file %s" % out)
        hotstuff.writeLayer(out, layer)
    elif layer.GetFeatureCount() > 0:
        if 'X' in poly and 'Y' in poly:
            out = options.get('prefix') + str(poly['X']) + "_" + str(poly['Y']) + ".geojson"
        elif 'name' in poly:
            out = options.get('prefix') + poly['name'] + ".geojson"
        else:
            out = options.get('prefix') +"0.geojson"
        # out = options['prefix'] + str(index) + ".geojson"
        # index += 1
        logging.info("Writing file %s" % out)
        hotstuff.writeLayer(out, layer)
    else:
        logging.error("No data to write!")
