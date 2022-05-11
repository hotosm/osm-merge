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

# By default process all the projects
projects=$(ls *-project.geojson)
if test x"${2}" != x; then
    projects="${2}-project.geojson"
fi

#
# Each Tasking Manager project is a single file
#
for project in ${projects}; do
    id=$(echo ${project} | cut -d '-' -f 1)
    if test ! -e ${id}-tasks.geojson; then
	curl -X GET "https://tasking-manager-tm4-production-api.hotosm.org/api/v2/projects/${id}/tasks/?as_file=false" -H "accept: application/json" > ${id}-tasks.geojson
    fi
    if test ! -e ${id}-buildings.geojson; then
	echo "No conflated building data for ${id}!"
	continue
    fi
    splitter.py -v -f ${id}-buildings.geojson -b ${id}-tasks.geojson -o footprints-
done
