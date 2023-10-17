#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023 Humanitarian OpenStreetMap Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
    
import argparse
import logging
import sys
import os
from sys import argv
from geojson import Point, Feature, FeatureCollection, dump, Polygon
import geojson
import psycopg2
from shapely.geometry import shape, Polygon, mapping
import shapely
from shapely import wkt, wkb
import xmltodict
from progress.bar import Bar, PixelBar
from progress.spinner import PixelSpinner
from codetiming import Timer
import concurrent.futures
from cpuinfo import get_cpu_info
from haversine import haversine, Unit
from thefuzz import fuzz, process
from osm_rawdata.postgres import uriParser, DatabaseAccess
# from conflator.geosupport import GeoSupport
from geosupport import GeoSupport

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']

class ConflateBuildings(object):
    def __init__(self,
                 dburi: str = None,
                 boundary: Polygon = None,
                 ):
        """
        This class conflates data that has been imported into a postgres
        database using the Underpass raw data schema.

        Args:
            dburi (str): The DB URI
            boundary (Polygon): The AOI of the project

        Returns:
            (ConflateDB): An instance of this object
        """
        self.postgres = list()
        self.uri = None
        if dburi:
            self.uri = uriParser(dburi)
            self.db = GeoSupport(dburi)
        self.boundary = boundary
        self.view = "ways_poly"

    def overlapDB(self,
                dburi: str,
                ):
        """
        Conflate buildings where all the data is in the same postgres database
        using the Underpass raw data schema.

        Args:
            dburi (str): The URI for the existing OSM data

        This is not fast for large areas!
        """
        if self.boundary:
            self.db.clipDB(self.boundary)

        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        # Find duplicate buildings in the same database
        sql = f"DROP VIEW IF EXISTS overlap_view;CREATE VIEW overlap_view AS SELECT ST_Area(ST_INTERSECTION(g1.geom::geography, g2.geom::geography)) AS area,g1.osm_id AS id1,g1.geom as geom1,g2.osm_id AS id2,g2.geom as geom2 FROM {self.view} AS g1, {self.view} AS g2 WHERE ST_OVERLAPS(g1.geom, g2.geom) AND (g1.tags->>'building' IS NOT NULL AND g2.tags->>'building' IS NOT NULL)"
        #sql = "SELECT * FROM (SELECT ways_view.id, tags, ROW_NUMBER() OVER(PARTITION BY geom ORDER BY ways_view.geom asc) AS Row, geom FROM ONLY ways_view) dups WHERE dups.Row > 1"
        # Make a new postgres VIEW of all overlapping or touching buildings
        log.info(f"Looking for overlapping buildings in \"{self.uri['dbname']}\", this make take awhile...")
        ## result = self.db.queryDB(sql)

        sql = "SELECT area,id1,geom1,id2,geom2 FROM overlap_view"
        ## result = self.db.queryDB(sql)
        result = list()
        features = list()
        for item in result:
            # First building identified
            entry = {'area': float(item[0]), 'id': int(item[1])}
            geom = wkb.loads(item[2])
            features.append(Feature(geometry=geom, properties=entry))
            # Second building identified
            entry['id'] = int(item[3])
            geom = wkb.loads(item[4])
            features.append(Feature(geometry=geom, properties=entry))

        log.debug(f"{len(features)} overlapping features found")

        log.debug(f"Clipping OSM database")
        ewkt = shape(self.boundary)
        uri = uriParser(dburi)
        log.debug(f"Extracting OSM subset from \"{uri['dbname']}\"")
        sql = f"DROP VIEW IF EXISTS osm_view CASCADE;CREATE VIEW osm_view AS SELECT osm_id,tags,geom FROM dblink('dbname={uri['dbname']}', 'SELECT osm_id,tags,geom FROM ways_poly') AS t1(osm_id int, tags jsonb, geom geometry) WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{ewkt}'), geom)"
        result = self.db.queryDB(sql)

        sql = f"DROP VIEW IF EXISTS dups_view;CREATE VIEW dups_view AS SELECT ST_Area(ST_INTERSECTION(g1.geom::geography, g2.geom::geography)) AS area,g1.osm_id AS id1,g1.geom as geom1,g2.osm_id AS id2,g2.geom as geom2 FROM {self.view} AS g1, osm_view AS g2 WHERE ST_OVERLAPS(g1.geom, g2.geom) AND (g1.tags->>'building' IS NOT NULL AND g2.tags->>'building' IS NOT NULL)"
        result = self.db.queryDB(sql)

        sql = "SELECT area,id1,geom1,id2,geom2 FROM dups_view"
        result = self.db.queryDB(sql)

        log.debug(f"{len(result)} duplicates found")
        features = list()
        for item in result:
            # First building identified
            entry = {'area': float(item[0]), 'id': int(item[1])}
            # FIXME: Do we want to filter by the size of the overlap ?
            # It's not exactly a reliable number since buildings are
            # different sizes.
            # if entry['area'] < 0.04:
            #     log.debug(f"FOO: {entry['area']}")
            #     continue
            geom = wkb.loads(item[2])
            features.append(Feature(geometry=geom, properties=entry))
            # Second building identified
            entry['id'] = int(item[3])
            geom = wkb.loads(item[4])
            features.append(Feature(geometry=geom, properties=entry))

        # FIXME: debug only!
        bar = open("foo.geojson", 'w')
        geojson.dump(FeatureCollection(features), bar)
        return FeatureCollection(features)

def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflateDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program conflates external data with existing features from OSM.",
        epilog="""
    This program conflates external datasets with OSM data using a postgresql database.
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-d", "--dburi", required=True, help="Source Database URI")
    parser.add_argument("-o", "--osmuri", required=True, help="OSM Database URI")
    parser.add_argument("-b", "--boundary", required=True,
                        help="Boundary polygon to limit the data size")
    # parser.add_argument("-o", "--outfile", help="Post conflation output file")

    args = parser.parse_args()

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(threadName)10s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)

    file = open(args.boundary, 'r')
    boundary = geojson.load(file)
    if 'features' in boundary:
        poly = boundary['features'][0]['geometry']
    else:
        poly = boundary['geometry']
    cdb = ConflateBuildings(args.dburi, poly)
    cdb.overlapDB(args.osmuri)
    # log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
