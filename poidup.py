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

#
# Note that this program is not designed to be fast, it's designed
# to be complete. It's a simple brute force algorithym. The input
# data file has to already be converted to OSM syntax of course.
# If a tag from the input file is found in any OSM features within
# a short distance, then the feature is flagged as a possible
# duplicate. Anything not flagged is likely new data.
#

import logging
import getopt
from sys import argv
import os
import epdb
import sys
import json
from geojson import Point, Polygon, Feature, FeatureCollection
import geojson
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
import psycopg2
from shapely.geometry import shape


# The tags we care about for this conflation
tags = ('amenity', 'leisure', 'information', 'tourism', 'sport')

indata = 'CWP_Facilities.geojson'
infile = open(indata, 'r')

outdata = 'cwp.geojson'
outfile = open(outdata, 'w')
outfeatures = list()

db = 'colorado'
connect = f"host=localhost dbname={db}"
dbshell = psycopg2.connect(connect)
dbcursor = dbshell.cursor()

tolerance = "0.1"
data = geojson.load(infile)
spin = Bar('Processing...', max=len(data['features']))

print("Data file contains %d features" % len(data['features']))
hits = False
for feature in data['features']:
    spin.next()
    tags = feature['properties']
    for tag in feature['properties']:
        if tag in tags:
            for key,value in feature['properties'].items():
                # print("%s = %s" % (key, value))
                geom = feature['geometry']
                wkt = shape(geom)
                query = "SELECT osm_id,geom,tags,ST_Distance(geom, ST_GeomFromEWKT(\'SRID=4326;%s\')) AS diff FROM nodes WHERE ST_Distance(geom, ST_GeomFromEWKT(\'SRID=4326;%s\')) < %s AND tags->>'%s'='%s'" % (wkt.wkt, wkt.wkt, tolerance, key, value.replace("\'", "&apos;"))
                # print(query)
                dbcursor.execute(query)
                all = dbcursor.fetchall()
                if len(all) > 0:
                    hits = True
    # If there is feature in OSM that matches any of the tags. and is very close,
    # flag it as a possible duplicate so we can find these in JOSM.
    if hits:
        feature['properties']['fixme'] = "Probably a duplicate!"
        # print(feature)
    outfeatures.append(feature)

print("Output file contains %d features" % len(outfeatures))
geojson.dump(FeatureCollection(outfeatures), outfile)
