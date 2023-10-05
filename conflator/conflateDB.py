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


# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info['count']


class ConflateDB(object):
    def __init__(self,
                 dburi: str,
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
        self.db = DatabaseAccess(dburi)
        self.boundary = boundary
        if boundary:
            self.clip(boundary, self.db)

    def clip(self,
             boundary: Polygon,
             db: DatabaseAccess,
             view: str = "ways_view",
             ):
        """
        Clip a data source by a boundary

        Args:
            boundary (Polygon): The filespec of the project AOI
            db (DatabaseAccess): A reference to the existing database connection
            view (str): The name of the view

        Returns:
            (bool): If the region was clipped sucessfully
        """
        remove = list()
        if not boundary:
            return False

        if 'features' in boundary:
            poly = boundary['features'][0]['geometry']
        else:
            poly = boundary["geometry"]
        ewkt = shape(poly)
        self.boundary = ewkt

        sql = f"DROP VIEW IF EXISTS {view};CREATE VIEW {view} AS SELECT * FROM ways_poly WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{ewkt}'), geom)"
        db.dbcursor.execute(sql)

        return True

    def dump(self):
        """Dump internal data"""
        # print(f"There are {len(self.data)} existing features")
        # if len(self.versions) > 0:
        #     for k, v in self.original.items():
        #         print(f"{k}(v{self.versions[k]}) = {v}")

    def conflateBuildings(self,
                          dburi: str = None,
                          ):
        """
        Conflate buildings where all the data is in the same postgres database
        using the Underpass raw data schema.

        This is not fast for large areas!

        Args:
            dburi (str): Optional database of OSM data
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        # Find duplicate buildings between two databases
        #sql = "SELECT ST_Area(ST_Transform(ST_INTERSECTION(g1.way, g2.way), 2167)),g1.osm_id,ST_Area(ST_Transform(g1.way, 2167)),g2.osm_id,ST_Area(ST_Transform(g2.way, 2167)) FROM boundary AS g1, boundary AS g2 WHERE ST_OVERLAPS(g1.way, g2.way);"

        # Find geometries that are an exact match, common if the same dataset is
        # imported more than once.
        sql = "SELECT * FROM (SELECT ways_view.osm_id, tags, ROW_NUMBER() OVER(PARTITION BY geom ORDER BY ways_view.geom asc) AS Row, geom FROM ONLY ways_view) dups WHERE dups.Row > 1"
        self.db.dbcursor.execute(sql)
        foo = list()
        for result in self.db.dbcursor.fetchall():
            geom = wkb.loads(result[3])
            foo.append(Feature(geometry=geom, properties=result[1]))

        # Find interescting building polygons
        sql = "SELECT ST_INTERSECTION(a.geom, b.geom),ST_AsText(a.geom)  FROM ways_view a, ways_view b WHERE a.osm_id != b.osm_id AND ST_INTERSECTS(a.geom, b.geom)"
        for result in self.db.dbcursor.fetchall():
            geom = wkb.loads(result[3])
            foo.append(Feature(geometry=geom, properties=result[1]))

        if dburi:
            # self.clip(self.boundary, self.db, "osm_view")
            uri = uriParser(dburi)
            # FIXME: fix weird issues with EWKT
            # sql = f"DROP VIEW IF EXISTS osm_view;CREATE VIEW osm_view AS SELECT * FROM dblink('dbname={uri['dbname']}', 'SELECT osm_id,geom FROM ways_poly WHERE ST_CONTAINS(ST_GeomFromEWKT(\"SRID=4326;{self.boundary}\"), geom)') AS t1(osm_id int, geom geometry)"
            sql = f"DROP VIEW IF EXISTS osm_view;CREATE VIEW osm_view AS SELECT * FROM dblink('dbname={uri['dbname']}', 'SELECT osm_id,version,geom FROM ways_poly') AS t1(osm_id int, version int, geom geometry)"
        self.db.dbcursor.execute(sql)
        sql = "SELECT b.osm_id,b.version, ST_INTERSECTION(a.geom, b.geom)::geography FROM ways_view a, osm_view b WHERE a.osm_id != b.osm_id AND ST_INTERSECTS(a.geom, b.geom)"
        # self.db.dbcursor.execute(sql)
        # for result in self.db.dbcursor.fetchall():
        #     geom = wkb.loads(result[3])
        #     foo.append(Feature(geometry=geom, properties=result[1]))


        # FIXME: debug only!
        bar = open("foo.geojson", 'w')
        geojson.dump(FeatureCollection(foo), bar)

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
    parser.add_argument("-d", "--dburi", required=True, help="Database URI")
    parser.add_argument("-c", "--category", required=True, help="")
    parser.add_argument("-b", "--boundary", required=True,
                        help="Boundary polygon to limit the data size")
    parser.add_argument("-o", "--outfile", help="Post conflation output file")

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

    boundary = open(args.boundary, 'r')
    poly = geojson.load(boundary)
    cdb = ConflateDB(args.dburi, poly)
    cdb.conflateBuildings("colorado")
    log.info(f"Wrote {args.outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
