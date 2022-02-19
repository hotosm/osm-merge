#!/usr/bin/python3
#
# Copyright (c) 2020, 2021 Humanitarian OpenStreetMap Team
#
# This file is part of Underpass.
#
#     Underpass is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Underpass is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with Underpass.  If not, see <https://www.gnu.org/licenses/>.

import logging
import getopt
from sys import argv
# import underpass
import os
from osgeo import ogr
# from geojson import Feature, Polygon, LineString, MultiLineString
# from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner

options = dict()
options["schema"] = "pgsnapshot";
options["osmin"] = None;
options["bldin"] = None;
options["tmin"] = None;
options["tmproj"] = None;

def usage():
    out = """
    --help(-h)      Get command line options
    --tmin(-t)      file or Tasking Manazger database URL (host@user:password/database)"
    --osmin(-o)     OSM Database URL (host@user:password/database)"
    --bldin(-b)     Building Database URL (host@user:password/database)"
    --project(-p)   Tasking Manager project ID to get boundary from a database
    --boundary(-b)  Specify a polygon as a boundary
    --schema(-s)    OSM database schema (pgsnapshot, ogr2ogr, osm2pgsql) defaults to \"%s\"
    """ % (options['schema'])
    print(out)
    quit()

if len(argv) <= 1:
    usage()

try:
    (opts, val) = getopt.getopt(argv[1:], "h,t:,o:,b:,p:,b:,s:",
        ["help", "tmin", "osmin", "bldin", "project", "boundary", "schema"])
except getopt.GetoptError as e:
    logging.error('%r' % e)
    usage(argv)
    quit()

for (opt, val) in opts:
    if opt == '--help' or opt == '-h':
        usage()
    elif opt == "--osmin" or opt == '-o':
        options['osmin'] = val
    elif opt == "--project" or opt == '-p':
        options['tmproj'] = val
    elif opt == "--tmin" or opt == '-t':
        options['tmin'] = val
    elif opt == "--boundary" or opt == '-b':
        options['boundary'] = val
    elif opt == "--buildings" or opt == '-b':
        options['bldin'] = val
    elif opt == "--schema" or opt == '-s':
        options['schema'] = val

#if options['osmdb'] is None and options['blddb'] is None and options['tmdb']:
#    usage()

#
# Get the project boundary from the Tasking Manager database
#

def getProjectBoundary():
    # FIXME: handle actual URL, don't assume localhost auth
    if options['tmproj'] is not None:
        connect = "PG: dbname=" + options['tmin']
        tmin = ogr.Open(connect)
    else:
        tmin = ogr.Open(options['tmin'])

    if options['tmproj'] is not None:
        sql = "SELECT id AS pid,ST_AsText(geometry) FROM projects WHERE id=" + str(options['tmproj'])
        layer = tmin.ExecuteSQL(sql)
        print(sql)
    elif options['tmin'] is not None:
        layer = tmin.GetLayer("tmproject")
    else:
        logging.error("Need to specify input data!")
    if layer is None:
        logging.error("No such project in the Tasking Manager database")
        return None

    # Create a bounding box. since we want a rectangular area to extract to fit a monitor window
    ring = ogr.Geometry(ogr.wkbLinearRing)
    extent = layer.GetExtent()
    ring.AddPoint(extent[0],extent[2])
    ring.AddPoint(extent[1], extent[2])
    ring.AddPoint(extent[1], extent[3])
    ring.AddPoint(extent[0], extent[3])
    ring.AddPoint(extent[0],extent[2])
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)

    return poly

#
#
#
# Get the boundary of the data to process
boundary = getProjectBoundary()
print(boundary)

