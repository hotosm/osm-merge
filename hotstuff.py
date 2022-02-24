#!/usr/bin/python3
#
# Copyright (c) 2022 Humanitarian OpenStreetMap Team
#
# This file is part of Conflator.
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
import sys
from osgeo import ogr
# from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner


def writeLayer(file=None, layer=None):
    if file is None:
        logging.error("Supply a filespec!")
        return
    if layer.GetFeatureCount() == 0:
        logging.error("Data is empty!!")
        return

    # import epdb;epdb.st()
    # GeoJson format is preferred
    drv = ogr.GetDriverByName("GeoJSON")
    # drv = ogr.GetDriverByName('ESRI Shapefile')

    # Delete the output file if it exists
    if os.path.exists(file):
        drv.DeleteDataSource(file)

    # Create the output file
    outfile  = drv.CreateDataSource(file)
    outlayer = outfile.CreateLayer("data", geom_type=ogr.wkbPolygon)

    # spin = PixelSpinner('Processing...')
    for feature in layer:
        # spin.next()
        outlayer.CreateFeature(feature)
    outfile.Destroy()

def makeBoundary(data=None):
    # Create a bounding box. since we want a rectangular area to extract
    # to fit a monitor window. Also many boundaries come as lines,
    # so close the polygon
    # print(data.GetGeometryName())
    ring = ogr.Geometry(ogr.wkbLinearRing)
    extent = data.GetEnvelope()
    ring.AddPoint(extent[0], extent[2])
    ring.AddPoint(extent[1], extent[2])
    ring.AddPoint(extent[1], extent[3])
    ring.AddPoint(extent[0], extent[3])
    ring.AddPoint(extent[0], extent[2])
    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)

    return poly

def getProjectBoundary(options=None):
    """Get the project boundary from the Tasking Manager database. or from a data file
    that has been downloaded from the Tasking Manager"""
    # FIXME: handle actual URL, don't assume localhost auth
    if len(options) is None:
        logging.error("Need to pass in the options")
        return None

    data = list()
    tmin = options['tmin']
    osmin = options['osmin']
    bound = options['boundary']
    tasks = options['tasks']
    project = options['project']
    layer = None
    multi = ogr.Geometry(ogr.wkbMultiPolygon)
    # Use Tasking Manager data for the boundary.
    if tmin is not None:
        if tmin[0:3] == "pg:" and project is None:
            logging.error("Need to specify a project ID when using the TM database")
            return None

        # Use TM data for the boundary or boundaries
        if tmin[0:3] == "pg:":
            if options['project'] is not None:
                logging.info("Opening TM database connection to: %s for %r" % (tmin[3:], project))
                connect = "PG: dbname=" + tmin[3:]
                tmp = ogr.Open(connect)
                if tasks:
                    sql = "SELECT projects.id AS pid,tasks.id AS tid,tasks.x,tasks,y AS tid,ST_AsText(tasks.geometry) FROM tasks,projects WHERE tasks.project_id=" + str(project) + " AND projects.id=" + str(project)
                    layer = tmp.ExecuteSQL(sql)
                else:
                    sql = "SELECT id AS pid,ST_AsText(geometry) FROM projects WHERE id=" + str(project)
                    print(sql)
                    layer = tmp.ExecuteSQL(sql)
        else:
            logging.info("Opening TM project boundary file: %s" % tmin)
            layer = tmp.GetLayer()

    # Use OSM postgres database for the boundaries. The default is admin_level 4, which
    # is regions. Regions or counties are a good size for data processing.
    if osmin is not None:
        if osmin[0:3] == "pg:":
            connect = "PG: dbname=" + osmin[3:]
            tmp = ogr.Open(connect)
            # Default osm2pgsql schema
            # sql = "SELECT name,wkb_geometry FROM multipolygons WHERE boundary='administrative' AND admin_level=" + str(options['admin'])
            # Modified schema using raw.lua
            sql = "SELECT tags->'name',tags->'boundary',tags->'admin_level' FROM ways_line WHERE tags->>'admin_level'='4' AND tags->>'name' IS NOT NULL"
            print(sql)
            layer = tmp.ExecuteSQL(sql)
        else:
            logging.info("Opening OSM project boundary file: %s" % osmin)
            tmp = ogr.Open(osmin)
            layer = tmp.GetLayer()

    if bound is not None:
        logging.info("Opening OSM project boundary file: %s" % osmin)
        tmp = ogr.Open(bound)
        layer = tmp.GetLayer()

    if layer is None:
        logging.error("No such project in the Tasking Manager database")
        return None

    if osmin is not None:
        logging.debug("%d features in %s" % (layer.GetFeatureCount(), osmin))
    elif bound is not None:
        logging.debug("%d features in %s" % (layer.GetFeatureCount(), bound))
    for poly in layer:
        admin = dict()
        boundary = makeBoundary(poly.GetGeometryRef())
        # print(boundary)
        admin['id'] = poly.GetField(0)
        admin['X'] = poly.GetField(1)
        admin['Y'] = poly.GetField(2)
        admin['boundary'] = boundary
        data.append(admin)
        #multi.AddGeometry(boundary)

    return data
