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
import epdb
import sys
from osgeo import ogr
# from geojson import Feature, Polygon, LineString, MultiLineString
from progress.bar import Bar, PixelBar
# from progress.spinner import PixelSpinner
import hotstuff
from codetiming import Timer


# All command line options
options = hotstuff.CommonOptions(argv)

def usage(options):
    out = options.usage()
    out += """
    Examples:
    The command: ./conflator.py -t tmsnap -p 8345 -b pg:kenya_foot -o pg:Kenya
    Reads from 3 data sources. The first one is a snapshot of the Tasking Manager database,
    and we want to use project 8345 as the boundary. Since the data files are huge, it's
    more efficient to work on subsets of all the data.

    The other two are prefixed with "pg", which defines them as a database URL instead of a file

    """
    print(out)
    quit()


timer = Timer()

# def findDuplicatesDatabase(self, osm, newbld):
#     """Find duplicate buildings between two databases"""
#     sql = "SELECT ST_Area(ST_Transform(ST_INTERSECTION(g1.way, g2.way), 2167)),g1.osm_id,ST_Area(ST_Transform(g1.way, 2167)),g2.osm_id,ST_Area(ST_Transform(g2.way, 2167)) FROM boundary AS g1, boundary AS g2 WHERE ST_OVERLAPS(g1.way, g2.way);"
#     pass

# Get the boundary of the data to process
if options.get("boundary"):
    rows = hotstuff.getProjectBoundary(options)
    if rows is None:
        logging.error("Boundary file should be a single polygon of a Tasking Manager project or an administrative boundary")
        quit()
else:
    rows = None

footprints = options.get('footprints')
if footprints[0:3] == "pg:":
    logging.info("Opening database connection to: %s" % footprints)
    connect = "PG: dbname=" + footprints[3:]
    if options.get('dbhost') != "localhost":
        connect += " host=" + options.get('dbhost')
        bldin = ogr.Open(connect)
else:
    logging.info("Opening buildings data file: %s" % footprints)
    bldin = ogr.Open(footprints)
buildings = bldin.GetLayer()
if buildings:
    logging.info("%d Buildings in %s" % (buildings.GetFeatureCount(), footprints))
else:
    logging.error("No buildings found in %s" % footprints)
    quit()

if rows:
    timer.start()
    buildings.ResetReading()
    buildings.SetSpatialFilter(rows[0]['boundary'])
    logging.debug("%d features after filtering" % (buildings.GetFeatureCount()))
    timer.stop()

osmdata = options.get('osmdata')
if osmdata[0:3] == "pg:":
    logging.info("Opening database connection to: %s" % osmdata)
    connect = "PG: dbname=" + osmdata[3:]
    if options.get('dbhost') != "localhost":
        connect += " host=" + options.get('dbhost')
        osmin = ogr.Open(connect)
else:
    logging.info("Opening OSM data file: %s" % osmdata)
    osmin = ogr.Open(osmdata)
osm = osmin.GetLayer()
if osm:
    logging.info("%d OSM Features in %s" % (osm.GetFeatureCount(), osmdata))
else:
    logging.error("No features found in %s" % osmdata)
    quit()

bfields = buildings.GetLayerDefn()

if rows:
    timer.start()
    osm.ResetReading()
    # FIXME: This drops most of the buildings for some reason
    #osm.SetAttributeFilter("tags->>\'building\'=\'yes\'")
    osm.SetSpatialFilter(rows[0]['boundary'])
    timer.stop()
    logging.debug("%d OSM features after filtering" % (osm.GetFeatureCount()))

# Output is GeoJson
drv = ogr.GetDriverByName("GeoJSON")

# Driver doesn't support deleting files, so handle it ourself
file = options.get('prefix') + "-test.geojson"
if os.path.exists(file):
    drv.DeleteDataSource(file)

# Create the output file
outfile  = drv.CreateDataSource(file)
outlayer = outfile.CreateLayer("buildings", geom_type=ogr.wkbPolygon)
fields = outlayer.GetLayerDefn()

newid = ogr.FieldDefn("id", ogr.OFTInteger)
outlayer.CreateField(newid)
bld = ogr.FieldDefn("building", ogr.OFTString)
outlayer.CreateField(bld)
src = ogr.FieldDefn("source", ogr.OFTString)
outlayer.CreateField(src)
status = ogr.FieldDefn("status", ogr.OFTString)
outlayer.CreateField(status)

# logging.info("Looking for unique buildings")
# timer.start()
# lyr1 = buildings
# lyr2 = osm
# lyr = lyr1.SymDifference(lyr2, outlayer)
# logging.debug("%d features in output dataset" % lyr.GetFeatureCount())
# timer.stop()
# quit()

if rows:
    # timer.start()
    sql = "SELECT geom FROM ways_poly WHERE tags->>\'building\' IS NOT NULL and ST_Within(geom, ST_GeomFromEWKT(\'SRID=4326;%s\'))" % rows[0]['boundary'].ExportToWkt()
    print(sql)
    layer1 = osmin.ExecuteSQL(sql)
    # layer1 = osm
    # layer1.SetSpatialFilter(rows[0]['boundary'])
    logging.debug("%d features in output dataset" % layer1.GetFeatureCount())
    # timer.stop()

# There is no boundary file, which is used to conflate two small datasets that have
# already been created with the same boundary
# if rows is None:
#     logging.debug("Using SymDifference")
#     timer.start()
#     lyr = buildings.SymDifference(osm, outlayer)
#     logging.info("Wrote output file \'%s\'" % file)
#     # for feature in lyr:
#     #     makeFeature(id, fields, msgeom)
#     timer.stop()
#     quit()

#epdb.st()
# bar = PixelSpinner('Processing...', max=layer1.GetFeatureCount())
bar = Bar('Processing...', max=buildings.GetFeatureCount())

id = 1
counter = 0
for msbld in buildings:
    bar.next()
    counter += 1
    msgeom = msbld.GetGeometryRef()
    mswkt = msgeom.ExportToWkt()
    dup = False
    for osmbld in osm:
        # print(osmbld.GetGeometryRef().ExportToWkt())
        osmgeom = osmbld.GetGeometryRef()
        intersect = osmgeom.Intersects(msgeom)
        touches = osmgeom.Touches(msgeom)
        overlap = osmgeom.Overlaps(msgeom)

        # print("GDAL: %r, %r, %r" % (intersect, touches, overlap))
        if intersect or overlap or touches:
            #         index = osmbld.GetFieldIndex('osm_id')
            # msbld.DumpReadable()
            logging.debug("Found intersecting buildings: %r" % counter)
            dup = True
        mscnt = msgeom.Centroid()
        osmcnt = osmgeom.Centroid()
        hit1 = osmgeom.Contains(mscnt)
        hit2 = msgeom.Contains(osmcnt)
        if hit1 and hit2:
            print("Found duplicate buildings %r, %r, %r" % (hit1, hit2, counter))
            dup = True
            break
    # If we have a duplicate, don't write anything to the outlayer
    if dup:
        continue

    logging.debug("New building ID: %s" % id)
    feature = hotstuff.makeFeature(id, fields, msgeom)
    outlayer.CreateFeature(feature)
    feature.Destroy()
    id += 1

logging.info("Wrote output file \'%s\'" % file)

outfile.Destroy()
#buildings.Destroy()
#osm.Destroy()
