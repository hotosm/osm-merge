#!/usr/bin/python3

# Copyright (c) 2022, 2023 OpenStreetMap US
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
# The lack of performance is tolerable with smaller input datasets,
# but obviously this won't scale. The conflator.py program is
# designed for larger datasets, so if that becomes necessary.

import logging
import argparse
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

# Instantiate logger
log = logging.getLogger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Conflate collected data with existing data"
    )
    parser.add_argument("-v", "--verbose", nargs="?", const="0", help="verbose output")
    parser.add_argument("-dn", "--dbname", default="colorado", help="Database name")
    parser.add_argument("-dh", "--dbhost", default="localhost", help="Database host")
    parser.add_argument("-i", "--infile", help="Input file")
    parser.add_argument("-o", "--outfile", default="poi-out.geojson", help="Output file")

    args = parser.parse_args()

    if len(argv) <= 1:
        parser.print_help()
        quit()

    # if verbose, dump to the terminal.
    if args.verbose is not None:
        root = logging.getLogger()
        log.setLevel(logging.DEBUG)

        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        root.addHandler(ch)

    # The tags we care about for this conflation
    tags = ('amenity', 'leisure', 'information', 'tourism', 'sport')

    if args.infile is None:
        logging.error("You must specify the input file to conflate!")
        parser.print_help()
        quit()
    else:
        indata = args.infile
        infile = open(indata, 'r')

    if args.outfile is not None:
        outdata = args.outfile
    outfile = open(outdata, 'w')
    outfeatures = list()

    if args.dbname is not None:
        db = args.dbname

    connect = f"dbname={db}"
    if args.dbhost is not None:
        connect += f" host={args.dbhost}"
    dbshell = psycopg2.connect(connect)
    dbcursor = dbshell.cursor()

    # The tolerance in meters for nearby features
    tolerance = "2"
    data = geojson.load(infile)
    spin = Bar('Processing...', max=len(data['features']))

    print("Data file contains %d features" % len(data['features']))
    # If there is feature in OSM that matches any of the tags. and
    # is very close, flag it as a possible duplicate so we can find
    # these in JOSM.
    for feature in data['features']:
        hits = False
        spin.next()
        tags = feature['properties']
        for tag in feature['properties']:
            if tag in tags:
                for key,value in feature['properties'].items():
                    # print("%s = %s" % (key, value))
                    geom = feature['geometry']
                    wkt = shape(geom)
                    # Use a Geography data type to get the answer in meters, which
                    # is easier to deal with than degress of the earth.
                    query = "SELECT osm_id,geom,tags FROM nodes WHERE ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;%s\')::geography) < %s AND tags->>'%s'='%s'" % (wkt.wkt, tolerance, key, value.replace("\'", "&apos;"))
                    #print(query)
                    dbcursor.execute(query)
                    all = dbcursor.fetchall()
                    if len(all) > 0:
                        # log.debug(f"NODE: {all}")
                        hits = True
                    if tag == 'amenity':
                        # Sometimes the duplicate is a polygon, really common for parking lots.
                        query = "SELECT osm_id,geom,tags FROM ways_poly WHERE ST_Distance(geom::geography, ST_GeogFromText(\'SRID=4326;%s\')::geography) < %s AND tags->>'%s'='%s' AND tags->>'amenity' IS NOT NULL" % (wkt.wkt, tolerance, key, value.replace("\'", "&apos;"))
                        # print(query)
                        dbcursor.execute(query)
                        all = dbcursor.fetchall()
                        if len(all) > 0:
                            # log.debug(f"WAY: {all}")
                            hits = True
                    # We only need one good hit to identify a duplicate
                    if hits:
                        break
        if hits:
            feature['properties']['fixme'] = "Probably a duplicate!"
            # print(feature)
        outfeatures.append(feature)

    print("Output file contains %d features" % len(outfeatures))
    geojson.dump(FeatureCollection(outfeatures), outfile)
