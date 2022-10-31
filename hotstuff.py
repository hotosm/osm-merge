#!/usr/bin/python3

# Copyright (c) 2022 Humanitarian OpenStreetMap Team
#
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import logging
import getopt
from sys import argv
# import underpass
import os
import sys
import epdb
import math
from osgeo import ogr
# from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
import urllib.request
from urllib.parse import urlparse
import threading
from codetiming import Timer

# Global mutex for the out layer
mutex = threading.Lock()

class CommonOptions(object):
    def __init__(self, argv=list()):
        self.options = dict()
        self.options["admin"] = 4  # The admin_level used when querying an OSM  database
        self.options["osmdata"] = None  # Raw OSM data imported with osm2pgsql
        self.options["footprints"] = None  # building footprints imported with ogr2ogr
        self.options["boundary"] = None    # The bouldary used for filtering the data
        # Tasking Manager options
        self.options["tmdata"] = None  # Tasking Manager database
        self.options["project"] = None  # Tasking Manmager project ID
        self.options["tasks"] = False   # When querying a TM database, get all tasks
        # database machine options, assumes a local database that the currently logged in user
        # can acess with no password
        self.options["dbhost"] = "localhost"
        self.options["dbuser"] = None
        self.options["dbpass"] = None
        self.options['prefix'] = "/tmp/tmproject-"
        self.options["schema"] = "pgsnapshot";
        # FIXME: only use staging for testing, since our test projects aren't in
        # the production system
        # self.options["tmhost"] = "tasking-manager-staging-api.hotosm.org"
        self.options["tmhost"] = "https://tasking-manager-tm4-production-api.hotosm.org"

        if len(argv) <= 1:
            self.usage()

        try:
            (opts, val) = getopt.getopt(argv[1:], "h,v,t:,b:,x:,f:,p:,s:,d:,u:,w:,a:o:",
                                        ["help", "verbose", "tmdata", "boundary", "osmdata",
                                         "footprints", "project", "schema", "dbhost", "dbuser",
                                         "dbpass", "adminlevel", "outdir", "splittasks"])
        except getopt.GetoptError as e:
            logging.error('%r' % e)
            self.usage(argv)
            quit()

        for (opt, val) in opts:
            if opt == '--help' or opt == '-h':
                print(self.usage())
                quit()
            elif opt == "--verbose" or opt == '-v':
                # Stream to the terminal for now
                # logging.basicConfig(filename='conflator.log',stream = sys.stdout,level=logging.DEBUG)
                logging.basicConfig(stream = sys.stdout,level=logging.DEBUG)
            elif opt == "--project" or opt == '-p':
                self.options['project'] = val
            elif opt == "--osmdata" or opt == '-x':
                self.options['osmdata'] = val
            elif opt == "--tmdata" or opt == '-t':
                self.options['tmdata'] = val
            elif opt == "--boundary" or opt == '-b':
                self.options['boundary'] = val
            elif opt == "--outdir" or opt == '-o':
                self.options['prefix'] = val
            elif opt == "--splittasks":
                self.options['tasks'] = True
            elif opt == "--dbhost" or opt == '-d':
                self.options['dbhost'] = val
            elif opt == "--user" or opt == '-u':
                self.options['dbuser'] = val
            elif opt == "--dbpass" or opt == '-w':
                self.options['dbpass'] = val
            elif opt == "--footprints" or opt == '-f':
                self.options['footprints'] = val
            elif opt == "--schema" or opt == '-s':
                self.options['schema'] = val

    def get(self, arg):
        if arg in self.options:
            return self.options[arg]
        else:
            logging.error("")
            return None

    def usage(self):
        out = """
        --help(-h)       Get command line options
        --verbose(-v)    Enable verbose output
        --boundary(-b)   Specify a multipolygon for boundaries, one file for each polygon
        --tmdata(-t)     Tasking Manager database to get boundaries if no boundary file
                         prefix with pg: for database usage, http for REST API
        --project(-p)    Tasking Manager project ID to get boundaries from database
        --splittasks     When using the Tasking Manager database, split into tasks
        --osmdata(-x)    OSM XML/PBF or OSM database to get boundaries (prefix with pg: if database)
        --admin(-a)      When querying the OSM database, this is the admin_level, (defaults to %d)
        --outdir(-o)     Output file prefix for output files (default \"%s\")
        --footprints(-f) File or building footprints Database URL (prefix with pg: if database)
        --schema         OSM database schema (pgsnapshot, ogr2ogr, osm2pgsql) defaults to \"%s\"
        --dbhost(-d)     Database host, defaults to \"localhost\"
        --dbuser(-u)     Database user, defaults to current user
        --dbpass(-w)     Database user, defaults to no password needed
        """ % (self.options['admin'], self.options['prefix'], self.options['schema'])
        return out


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
    outfile  = drv.CreateDataSource(file.replace(" ", "_"))
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
    if options is None:
        logging.error("Need to pass in the options")
        return None

    data = list()
    tmdb = options.get('tmdata')
    osmdata = options.get('osmdata')
    bound = options.get('boundary')
    tasks = options.get('tasks')
    project = options.get('project')
    dbhost = options.get('dbhost')
    tmhost = options.get("tmhost")

    layer = None
    multi = ogr.Geometry(ogr.wkbMultiPolygon)
    # Use Tasking Manager data for the boundary.
    if tmdb is not None:
        if tmdb[0:3] == "pg:" and project is None:
            logging.error("Need to specify a project ID when using the TM database")
            return None

        # Use TM data for the boundary or boundaries
        if tmdb[0:3] == "pg:":
            if options['project'] is not None:
                logging.info("Opening TM database connection to: %s for %r" % (tmdb[3:], project))
                connect = "PG: dbname=" + tmdb[3:]
                if dbhost != "localhost":
                    connect += " host=" + dbhost
                tmp = ogr.Open(connect)
                if tasks:
                    sql = "SELECT projects.id AS pid,tasks.id AS tid,tasks.x,tasks,y AS tid,ST_AsText(tasks.geometry) FROM tasks,projects WHERE tasks.project_id=" + str(project) + " AND projects.id=" + str(project)
                    layer = tmp.ExecuteSQL(sql)
                else:
                    sql = "SELECT id AS pid,ST_AsText(geometry) FROM projects WHERE id=" + str(project)
                    # print(sql)
                    layer = tmp.ExecuteSQL(sql)
    elif project is not None:
        if tasks:
            request = tmhost + "/api/v2/projects/%s/tasks/?as_file=false" % project
            outfile = "%s-tasks.geojson" % project
        else:
            request = tmhost + "/api/v2/projects/%s/queries/aoi/?as_file=false" % project
            outfile = "%s-project.geojson" % project
        headers = dict()
        headers['Content-Type'] = 'accept:application/json'
        req = urllib.request.Request(request, headers=headers)
        x = urllib.request.urlopen(req)
        output = x.read().decode('utf-8')
        # logging.debug("FIXME: %r" % output)
        tmp = open(outfile, "w")
        tmp.write(output)
        tmp.close()
        tmp = ogr.Open(outfile)
        layer = tmp.GetLayer()

    # Use OSM postgres database for the boundaries. The default is admin_level 4, which
    # is regions. Regions or counties are a good size for data processing.
    if osmdata is not None and bound is None and project is None:
        if osmdata[0:3] == "pg:":
            connect = "PG: dbname=" + osmdata[3:]
            if dbhost != "localhost":
                connect += " host=" + dbhost
            tmp = ogr.Open(connect)
            if tmp is None:
                logging.error("Couldn't open %s" % osmdata)
            # Default osm2pgsql schema
            # sql = "SELECT name,wkb_geometry FROM multipolygons WHERE boundary='administrative' AND admin_level=" + str(options['admin'])
            # Modified schema using raw.lua
            sql = "SELECT tags->'name',tags->'boundary',tags->'admin_level' FROM ways_line WHERE tags->>'admin_level'='4' AND tags->>'name' IS NOT NULL"
            print(sql)
            layer = tmp.ExecuteSQL(sql)
        else:
            logging.info("Opening OSM project boundary file: %s" % osmdata)
            tmp = ogr.Open(osmdata)
            if tmp is None:
                logging.error("Couldn't open %s" % osmdata)
                return None
            layer = tmp.GetLayer()

    if bound is not None:
        logging.info("Opening boundary file: %s" % bound)
        tmp = ogr.Open(bound)
        if tmp is None:
            logging.error("Couldn't open %s" % bound)
            return None
        layer = tmp.GetLayer()

    if layer is None:
        logging.error("No such project in the Tasking Manager database")
        return None

    if osmdata is not None and bound is None:
        logging.debug("%d features in %s" % (layer.GetFeatureCount(), osmdata))
    if bound is not None:
        logging.debug("%d features in %s" % (layer.GetFeatureCount(), bound))
    for poly in layer:
        admin = dict()
        boundary = makeBoundary(poly.GetGeometryRef())
        # print("POLY: %r" % poly.GetGeometryRef().GetGeometryCount())
        index = poly.GetFieldIndex('name')
        if index >= 0:
            admin['name'] = poly.GetField(index)
        if boundary.GetGeometryCount() > 1 or poly.GetFieldCount() > 0:
            admin['id'] = poly.GetField(0)
            admin['X'] = poly.GetField(1)
            admin['Y'] = poly.GetField(2)
        admin['boundary'] = boundary
        data.append(admin)

    return data

def makeFeature(id, fields, geom):
    feature = ogr.Feature(fields)
    feature.SetField("id", id)
    feature.SetField("building", "yes")
    feature.SetField("source", "bing")
    feature.SetGeometry(geom)
    return feature

def isWeird(geom):
    """Is this geometry weird ? It's probably in a plowed field."""
    poly = geom.GetGeometryRef(0)
    if poly.GetPointCount() > 12:
        return True
    else:
        return False

def isSquare(geom):
    """Is this geometry a square ?"""
    # Is this a rectangle or square ?
    poly = geom.GetGeometryRef(0)
    if poly.GetPointCount() == 5:
        prev = 0.0
        for i in range(4):
            line = ogr.Geometry(ogr.wkbLineString)
            lat = poly.GetPoint(i)[0]
            lon = poly.GetPoint(i)[1]
            line.AddPoint(lat, lon)
            lat = poly.GetPoint(i+1)[0]
            lon = poly.GetPoint(i+1)[1]
            line.AddPoint(lat, lon)
            if math.isclose(prev, line.Length(), rel_tol=1e-09, abs_tol=0.00001):
                return True
            prev = line.Length()
        return False

def conflate(buildings, osm, spin):
    """Conflate a building against OSM data."""
    timer = Timer()
    new = list()
    # global mutex
    for msbld in buildings:
        spin.next()
        msgeom = msbld.GetGeometryRef()
        dup = False
        # timer.start()
        # import epdb ; epdb.st()
        for osmbld in osm:
            osmgeom = osmbld.GetGeometryRef()
            intersect = osmgeom.Intersects(msgeom)
            overlap = osmgeom.Overlaps(msgeom)
            # print("GDAL: %r, %r" % (intersect, overlap))
            if intersect or overlap:
                # logging.debug("Found intersecting buildings: %r (%r)" % (msbld.GetFID(), osmbld.GetField(0)))
                dup = True
                break
            mscnt = msgeom.Centroid()
            osmcnt = osmgeom.Centroid()
            hit1 = osmgeom.Within(mscnt)
            hit2 = msgeom.Within(osmcnt)
            dist = mscnt.Distance(osmcnt)
            # if (hit1 or hit2) dist < 1.0e-08:
            if (hit1 or hit2) or dist < 2.0e-08:
                dup = True
                logging.debug("Found duplicate buildings %r, %r: %r vs %r (%r)" % (hit1, hit2,
                                            msbld.GetFID(), osmbld.GetField(0), dist))
                break

            #    if not intersect and not overlap and not hit1 and not hit2:
        if not dup:
            dup = False
            # logging.debug("New building ID: %s" % msbld.GetFID())
            new.append(msbld)
            #feature = makeFeature(msbld.GetFID(), fields, msgeom)
            #outlayer.CreateFeature(feature)
            #feature.Destroy()
        # timer.stop()
    return new
