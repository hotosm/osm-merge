#!/bin/bash

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
# This script creates the smaller data files used for more efficient conflation.
#
if test x"$1" = x; then
    echo "ERROR: please specify the country name, which should match the database name"
    exit
fi

if test x"$1" = x; then
    echo "Guessing the probable country name ?..."
    country=$(basename $PWD | tr "[:upper:]" "[:lower:]")
    echo -n "Is ${country} correct ? y to continue "
    read answer
    if test x"${answer}" != x"y"; then
	echo "ERROR: please specify the country name, which should match the database name"
	exit
    fi
else
    country="$1"
fi
echo "Processing country \"${country}\""

# By default process all the projects
projects=$(ls *-project.geojson)
if test x"${2}" != x; then
    projects="${2}-project.geojson"
fi

echo -n "Checking to see if the footprint data is in a database..."
exists=$(psql -l | grep -c ${country}_foot)

dbname=""
if expr "${exists}" = 1 > /dev/null; then
    echo " yes \"${country}_foot\" exists"
    dbname=${country}_foot
fi

# the conflator program should be in your path
PATH="/data/conflator.git:${PATH}"

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
for project in ${projects}; do
    id=$(echo ${project} | cut -d '-' -f 1)
    ogr2ogr -progress -f "GeoJSON" -clipsrc ${id}-project.geojson ${id}-osm.geojson ${country}-osm.geojson
    ogr2ogr -progress -f "GeoJSON" -clipsrc ${id}-project.geojson ${id}-ms.geojson ${country}-ms.geojson
done
