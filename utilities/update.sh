#!/bin/bash

#
# This script conflates all the files in this sub directory
#

if test x"$1" = x; then
    echo "ERROR: please specify the country name, which should match the database name"
    exit
fi
country="$1"
exists=$(psql -l | grep -c ${country}_foot)
echo "Processing country ${country}"

dbname=""
if expr "${exists}" = 1 > /dev/null; then
    dbname=${country}_foot
fi

bound=$(basename)

# the conflator program should be in your path
PATH="/data/conflator.git:${PATH}"
#
# Each Tasking Manager project is a single file
#
for project in *-project.geojson; do
    id=$(echo ${project} | cut -d '-' -f 1)
    if test ! -e ${id}-osm.geojson &&  test ! -e ${id}-ms.geojson; then
	echo "ERROR: Data files ${id}-*.geojson don't exist! Run ./clipsrc first to produce them"
	continue
    fi
    if test ! -e ${id}-test.geojson; then
	if test x"${dbname}" != x; then
	   echo conflator.py -v -x ${id}-osm.geojson -f ${id}-ms.geojson -o ${id}
	   echo mv ${id}-test.geojson ${id}-buildings.geojson
	fi
    fi
done
