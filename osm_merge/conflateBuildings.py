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

import geojson
from codetiming import Timer
from cpuinfo import get_cpu_info
from geojson import Feature, FeatureCollection, Polygon

# from osm_merge.geosupport import GeoSupport
from geosupport import GeoSupport
from osm_rawdata.postgres import uriParser
from shapely import wkb
from shapely.geometry import Polygon, shape

# Instantiate logger
log = logging.getLogger(__name__)

# The number of threads is based on the CPU cores
info = get_cpu_info()
cores = info["count"]


class ConflateBuildings(object):
    def __init__(
        self,
        dburi: str = None,
        boundary: Polygon = None,
    ):
        """This class conflates data that has been imported into a postgres
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
        self.filter = list()

    def addSourceFilter(
        self,
        source: str,
    ):
        """Add to a list of suspect bad source datasets"""
        self.filter.append(source)

    def overlapDB(
        self,
        dburi: str,
    ):
        """Conflate buildings where all the data is in the same postgres database
        using the Underpass raw data schema.

        Args:
            dburi (str): The URI for the existing OSM data

        This is not fast for large areas!
        """
        timer = Timer(text="conflateData() took {seconds:.0f}s")
        timer.start()
        # Find duplicate buildings in the same database
        # sql = f"DROP VIEW IF EXISTS overlap_view;CREATE VIEW overlap_view AS SELECT ST_Area(ST_INTERSECTION(g1.geom::geography, g2.geom::geography)) AS area,g1.osm_id AS id1,g1.geom as geom1,g2.osm_id AS id2,g2.geom as geom2 FROM {self.view} AS g1, {self.view} AS g2 WHERE ST_OVERLAPS(g1.geom, g2.geom) AND (g1.tags->>'building' IS NOT NULL AND g2.tags->>'building' IS NOT NULL)"
        # sql = "SELECT * FROM (SELECT ways_view.id, tags, ROW_NUMBER() OVER(PARTITION BY geom ORDER BY ways_view.geom asc) AS Row, geom FROM ONLY ways_view) dups WHERE dups.Row > 1"
        # Make a new postgres VIEW of all overlapping or touching buildings
        # log.info(f"Looking for overlapping buildings in \"{self.uri['dbname']}\", this make take awhile...")
        # print(sql)
        # Views must be dropped in the right order
        sql = (
            "DROP TABLE IF EXISTS dups_view CASCADE; DROP TABLE IF EXISTS osm_view CASCADE;DROP TABLE IF EXISTS ways_view CASCADE;"
        )
        result = self.db.queryDB(sql)

        if self.boundary:
            self.db.clipDB(self.boundary)

        log.debug("Clipping OSM database")
        ewkt = shape(self.boundary)
        uri = uriParser(dburi)
        log.debug(f"Extracting OSM subset from \"{uri['dbname']}\"")
        sql = f"CREATE TABLE osm_view AS SELECT osm_id,tags,geom FROM dblink('dbname={uri['dbname']}', 'SELECT osm_id,tags,geom FROM ways_poly') AS t1(osm_id int, tags jsonb, geom geometry) WHERE ST_CONTAINS(ST_GeomFromEWKT('SRID=4326;{ewkt}'), geom) AND tags->>'building' IS NOT NULL"
        # print(sql)
        result = self.db.queryDB(sql)

        sql = "CREATE TABLE dups_view AS SELECT ST_Area(ST_INTERSECTION(g1.geom::geography, g2.geom::geography)) AS area,g1.osm_id AS id1,g1.geom as geom1,g1.tags AS tags1,g2.osm_id AS id2,g2.geom as geom2, g2.tags AS tags2 FROM ways_view AS g1, osm_view AS g2 WHERE ST_INTERSECTS(g1.geom, g2.geom) AND g2.tags->>'building' IS NOT NULL"
        print(sql)
        result = self.db.queryDB(sql)

    def cleanDuplicates(self):
        """Delete the entries from the duplicate building view.

        Returns:
            (FeatureCollection): The entries from the datbase table
        """
        log.debug("Removing duplicate buildings from ways_view")
        sql = "DELETE FROM ways_view WHERE osm_id IN (SELECT id1 FROM dups_view)"

        result = self.db.queryDB(sql)
        return True

    def getNew(self):
        """Get only the new buildings

        Returns:
            (FeatureCollection): The entries from the datbase table
        """
        sql = "SELECT osm_id,geom,tags FROM ways_view"
        result = self.db.queryDB(sql)
        features = list()
        for item in result:
            # log.debug(item)
            entry = {"osm_id": item[0]}
            entry.update(item[2])
            geom = wkb.loads(item[1])
            features.append(Feature(geometry=geom, properties=entry))

        log.debug(f"{len(features)} new features found")
        return FeatureCollection(features)

    def findHighway(
        self,
        feature: Feature,
    ):
        """Find the nearest highway to a feature

        Args:
            feature (Feature): The feature to check against
        """
        pass

    def getDuplicates(self):
        """Get the entries from the duplicate building view.

        Returns:
            (FeatureCollection): The entries from the datbase table
        """
        sql = "SELECT area,id1,geom1,tags1,id2,geom2,tags2 FROM dups_view"
        result = self.db.queryDB(sql)
        features = list()
        for item in result:
            # log.debug(item)
            # First building identified
            entry = {"area": float(item[0]), "id": int(item[1])}
            geom = wkb.loads(item[2])
            entry.update(item[3])
            features.append(Feature(geometry=geom, properties=entry))

            # Second building identified
            entry = {"area": float(item[0]), "id": int(item[4])}
            entry["id"] = int(item[4])
            geom = wkb.loads(item[5])
            entry.update(item[6])
            # FIXME: Merge the tags from the buildings into the OSM feature
            # entry.update(item[3])
            features.append(Feature(geometry=geom, properties=entry))

        log.debug(f"{len(features)} duplicate features found")
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
    parser.add_argument("-b", "--boundary", required=True, help="Boundary polygon to limit the data size")
    # parser.add_argument("-o", "--outfile", help="Post conflation output file")

    args = parser.parse_args()

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(threadName)10s - %(name)s - %(levelname)s - %(message)s")
        ch.setFormatter(formatter)
        log.addHandler(ch)

    file = open(args.boundary, "r")
    boundary = geojson.load(file)
    if "features" in boundary:
        poly = boundary["features"][0]["geometry"]
    else:
        poly = boundary["geometry"]
    cdb = ConflateBuildings(args.dburi, poly)
    cdb.overlapDB(args.osmuri)
    features = cdb.getDuplicates()

    # FIXME: These are only for debugging
    file = open("foo.geojson", "w")
    geojson.dump(features, file)
    log.info("Wrote foo.geojson for duplicates")

    cdb.cleanDuplicates()
    features = cdb.getNew()
    file = open("bar.geojson", "w")
    geojson.dump(features, file)

    log.info("Wrote bar.geojson for new buildings")


if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
