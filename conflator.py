#!/usr/bin/python3

# Copyright (c) 2022 Humanitarian OpenStreetMap Team
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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
from progress.spinner import PixelSpinner
import hotstuff
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from time import sleep


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

# Copy the data into memory for better performance
memdrv = ogr.GetDriverByName("MEMORY")
msmem = memdrv.CreateDataSource('msmem')
msmem.CopyLayer(bldin.GetLayer(), "msmem")
buildings = msmem.GetLayer()
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
    osm = osmin.GetLayerByName("ways_poly")
else:
    logging.info("Opening OSM data file: %s" % osmdata)
    osmin = ogr.Open(osmdata)

# Copy the data into memory for better performance
osmem = memdrv.CreateDataSource('osmem')
osmem.CopyLayer(osmin.GetLayer(), "osmem")
osm = osmem.GetLayer()
if osm:
    logging.info("%d OSM Features in %s" % (osm.GetFeatureCount(), osmdata))
else:
    logging.error("No features found in %s" % osmdata)
    quit()

# bfields = buildings.GetLayerDefn()

# If a boundary was specified, use it to limit the input data
if rows:
    timer.start()
    osm.ResetReading()
    osm.SetSpatialFilter(rows[0]['boundary'])
    if osmdata[0:3] == "pg:":
        osm.SetAttributeFilter("tags->>'building' IS NOT NULL")
    timer.stop()
    logging.debug("%d OSM features after filtering" % (osm.GetFeatureCount()))

# Output is in memory, gets written later after any post processing.
drv = ogr.GetDriverByName("MEMORY")

# Driver doesn't support deleting files, so handle it ourself
file = options.get('prefix') + "test.geojson"
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

bar = Bar('Processing...', max=buildings.GetFeatureCount())
info = get_cpu_info()
cores = info['count']

logging.info("Writing to output file \'%s\'" % file)

# Break the footprint file into chunks, one for each thread.
# FIXME: There's gotta be a python module that does this...
subset = list()
sliced = list()
chunk =  round(buildings.GetFeatureCount()/cores)
i = 0
cycle = range(0, buildings.GetFeatureCount(), chunk)
for bld in buildings:
    # print(bld.GetGeometryType())
    subset.append(bld)
    if i == chunk:
        i = 0
        sliced.append(subset)
        subset = list()
    i += 1

# The data in the memory layer is not thread safe, so each thread needs
# it's own copy. Access is all read-only, but if multiple threads try
# to read data from the same memory layer, it will conflict.
osmchunks = list()
os = memdrv.CreateDataSource('osmem')
for i in range(0, cores + 1):
    osmchunks.append(os.CopyLayer(osm, "osm1"))
logging.debug("%d chunks" % (len(osmchunks)))

# Fire up one thread for each CPU core to process the data.
newblds = list()
spin = PixelSpinner('Processing...')
logging.info("processing data, please wait, this may take awhile...")
i = 0
futures = list()
with concurrent.futures.ThreadPoolExecutor(max_workers = cores) as executor:
    # timer.start()
    for block in sliced:
        # memdrv = ogr.GetDriverByName("MEMORY")
        future = executor.submit(hotstuff.conflate, block, osmchunks[i], spin)
        if i < cores:
            i += 1
        else:
            i = 0
        futures.append(future)
    for future in concurrent.futures.as_completed(futures):
        # print("RESULT: %r vs %r" % (len(newblds), len(future.result())))
        futures.remove(future)
        if len(newblds) == 0:
            newblds = future.result()
        else:
            newblds += future.result()
    executor.shutdown()
    # timer.stop()

filespec = "foo.geojson"
outdrv = ogr.GetDriverByName("GeoJson")
outf  = outdrv.CreateDataSource(filespec)
outlyr = outf.CreateLayer("buildings", geom_type=ogr.wkbPolygon)

logging.info("Writing to output file \'%s\', this may take awhile..." % filespec)
# print("RESULT: %r" % (len(newblds)))
for msbld in newblds:
    # bar.next()
    msgeom = msbld.GetGeometryRef()
    feature = hotstuff.makeFeature(msbld.GetFID(), fields, msgeom)
    outlyr.CreateFeature(feature)
    feature.Destroy()
outf.Destroy()

print("")
logging.info("Wrote output file \'%s\'" % file)

outfile.Destroy()
