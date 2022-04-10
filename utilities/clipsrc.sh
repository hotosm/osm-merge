#!/bin/bash

#
# This script creates the smaller data files used for more efficient conflation.
#
if test x"$1" = x; then
    echo "ERROR: please specify the country name, which should match the database name"
    exit
fi
country="$1"
# dbs=$(psql -l | grep ${country}_foot | tr -s ' ' | cut -d ' ' -f 2)
exists=$(psql -l | grep -c ${country}_foot)

dbname=""
if expr "${exists}" = 1 > /dev/null; then
    dbname=${country}_foot
fi

echo "Processing country ${country}"

# OSM buildings are in a database
if test ! -e  ${country}-osm.geojson; then
    echo "Collecting OSM buildings within ${country}..."
    ogr2ogr -progress -f "GeoJSON" ${country}-osm.geojson  -sql "SELECT osm_id,tags,geom FROM ways_poly WHERE tags->>'building' IS NOT NULL" -nlt POLYGON PG:"dbname=${country}"
fi

# MS Building footprins are in a geojson file
if test ! -e  ${country}-ms.geojson; then
    echo "Collecting MS buildings within ${country}..."
    ogr2ogr -progress -f "GeoJSON" ${country}-ms.geojson -nlt POLYGON PG:"dbname=${country}_foot"
fi

#
# Each Tasking Manager project is a single file
#
for project in *-project.geojson; do
    id=$(echo ${project} | cut -d '-' -f 1)
    echo ogr2ogr -progress -f "GeoJSON" -clipsrc ${id}-project.geojson ${id}-osm.geojson ${country}-osm.geojson 
    echo ogr2ogr -progress -f "GeoJSON" -clipsrc ${id}-project.geojson ${id}-ms.geojson ${country}-ms.geojson 
done
