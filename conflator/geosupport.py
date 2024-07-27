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
from osm_rawdata.pgasync import PostgresClient

# Instantiate logger
log = logging.getLogger(__name__)


class GeoSupport(object):
    def __init__(self,
                 dburi: str = None,
                 config: str = None,
                 ):
        """
        This class conflates data that has been imported into a postgres
        database using the Underpass raw data schema.

        Args:
            dburi (str, optional): The database URI
            config (str, optional): The config file from the osm-rawdata project

        Returns:
            (GeoSupport): An instance of this object
        """
        self.db = None
        self.dburi = dburi
        self.config = config

    async def initialize(self,
                        dburi: str = None,
                        config: str = None,
                        ):
        """
        When async, we can't initialize the async database connection,
        so it has to be done as an extrat step.

        Args:
            dburi (str, optional): The database URI
            config (str, optional): The config file from the osm-rawdata project
        """
        if dburi:
            self.db = PostgresClient()
            await self.db.connect(dburi)
        elif self.dburi:
            self.db = PostgresClient()
            await self.db.connect(self.dburi)

        if config:
            await self.db.loadConfig(config)
        elif self.config:
            await self.db.loadConfig(config)

    async def dump(self):
        print(f"Config category \" {self.config}\"")
        for db in self.postgres:
            if db.is_closed():
                print(f"Database URI \"{db.dburi}\" is closed")
            else:
                print(f"Database URI \"{db.dburi}\" is open")

    async def clipDB(self,
             boundary: Polygon,
             db: PostgresClient = None,
             view: str = "ways_view",
             ):
        """
        Clip a database table by a boundary

        Args:
            boundary (Polygon): The AOI of the project
            db (PostgresClient): A reference to the existing database connection
            view (str): The name of the new view

        Returns:
            (bool): If the region was clipped sucessfully
        """
        remove = list()
        if not boundary:
            return False

        ewkt = shape(boundary)

        # Create a new postgres view
        # FIXME: this should be a temp view in the future, this is to make
        # debugging easier.
        sql = f"DROP VIEW IF EXISTS {view} CASCADE ;CREATE VIEW {view} AS SELECT * FROM ways_poly WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{ewkt}'), geom)"
        # log.debug(sql)
        if db:
            result = await db.queryDB(sql)
        elif self.db:
            result = await self.db.queryDBl(sql)
        else:
            return False

        return True

    async def queryDB(self,
                sql: str = None,
                db: PostgresClient = None,
                ) -> list:
        """
        Query a database table

        Args:
            db (PostgreClient, optional): A reference to the existing database connection
            sql (str): The SQL query to execute

        Returns:
            (list): The results of the query
        """
        result = list()
        if not sql:
            log.error(f"You need to pass a valid SQL string!")
            return result

        if db:
            result = db.queryLocal(sql)
        elif self.db:
            result = self.db.queryLocal(sql)

        return result

    async def clipFile(self,
                boundary: Polygon,
                data: FeatureCollection,
                ):
        """
        Clip a database table by a boundary

        Args:
            boundary (Polygon): The filespec of the project AOI
            data (FeatureCollection): The data to clip

        Returns:
            (FeatureCollection): The data within the boundary
        """
        new = list()
        if len(self.data) > 0:
            for feature in self.data["features"]:
                shapely.from_geojson(feature)
                if not shapely.contains(ewkt, entry):
                    log.debug(f"CONTAINS {entry}")
                    new.append(feature)
                    #  del self.data[self.data['features']]

        return new

    async def outputOSM(self,
                  data: FeatureCollection,
                  outfile: str = None,
                  ):
        """
        Output in OSM XML format

        Args:
            data (FeatureCollection): The data to convert
            outfile (str): The filespec of the OSM file

        Returns:
            (list): The OSM XML output
        """
        out = list()
        osmf = OsmFile(outfile)
        for feature in data:
            if feature["geometry"]["type"] == "Polygon":
                feature["refs"] = list()
                out.append(osmf.createWay(feature, True))
            elif feature["geometry"]["type"] == "Point":
                out.append(osmf.createNode(feature, True))

        if outfile:
            osmf.write(out)
            log.info(f"Wrote {outfile}")

        return out

    async def outputJOSM(self,
                  data: FeatureCollection,
                  outfile: str = None,
                  ):
        """
        Output in OSM XML format

        Args:
            data (FeatureCollection): The data to convert
            outfile (str): The filespec of the GeoJson file

        Returns:
            (bool): Whether the creation of the output file worked
        """
        if outfile:
            file = open(outfile, 'w')
            geojson.dump(FeatureCollection(features), file)
            return True
        else:
            return False

async def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="conflateDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program contains common support used by the other programs",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-d", "--dburi", required=True, help="Database URI")
    parser.add_argument("-b", "--boundary", required=True,
                        help="Boundary polygon to limit the data size")

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

    db = DatabaseAccess(args.dburi, poly)
    cdb = GeoSupport()

    cdb.clipDB(poly, db)
    sql = "SELECT COUNT(osm_id) FROM ways_view"
    result = await cdb.queryDB(sql, db)
    if type(result) == list:
        log.debug(f"Returned: {result[0]}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
