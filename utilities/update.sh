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
# This script conflates all the files in this sub directory
#

# By default process all the projects
projects=$(ls *-project.geojson)
if test x"${2}" != x; then
    projects="${2}-project.geojson"
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

echo -n "Checking to see if the footprint data is in a database..."
exists=$(psql -l | grep -c ${country}_foot)

dbname=""
if expr "${exists}" = 1 > /dev/null; then
    echo " yes \"${country}_foot\" exists"
    dbname=${country}_foot
fi

# the conflator program should be in your path
PATH="/data/conflator.git:${PATH}"

#
# Each Tasking Manager project is a single file
#
for project in ${projects}; do
    id=$(echo ${project} | cut -d '-' -f 1)
    if test ! -e ${id}-osm.geojson &&  test ! -e ${id}-ms.geojson; then
	echo "ERROR: Data files ${id}-*.geojson don't exist! Run ./clipsrc first to produce them"
	continue
    fi
    if test ! -e ${id}-test.geojson; then
	if test x"${dbname}" != x; then
	   conflator.py -v -x ${id}-osm.geojson -f ${id}-ms.geojson -o ${id}
	   mv ${id}-test.geojson ${id}-buildings.geojson
	fi
    fi
done
