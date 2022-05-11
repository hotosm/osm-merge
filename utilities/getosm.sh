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

project=$1
file=/tmp/q.txt

# By default process all the projects
projects=$(ls *-project.geojson)
if test x"${1}" != x; then
    projects="${1}-project.geojson"
fi


for project in ${projects}; do
    id=$(echo ${project} | cut -d '-' -f 1)
    extent=$(ogrinfo -ro -al ${id}-project.geojson | grep Extent | tr -d ')(,' | sed --e 's/- //')
    x1=$(echo ${extent} | cut -d ' ' -f 3)
    y1=$(echo ${extent} | cut -d ' ' -f 2)
    x2=$(echo ${extent} | cut -d ' ' -f 5)
    y2=$(echo ${extent} | cut -d ' ' -f 4)
done

cat <<EOF > ${file}
(
  way["building"](${x1},${y1},${x2},${y2});
  node(${x1},${y1},${x2},${y2});
  >;
);
out meta;

EOF
echo "Using Overpass QL to get fresh OSM data"

wget --post-file=${file} http://overpass-api.de/api/interpreter

mv interpreter ${id}-osm.osm
