#!/bin/bash

# Copyright (c) 2022 OpenStreetMap US
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
# These functions are used by the index.sh script
#
outfile="index.html"

header()
{
    local title="$1"
    cat <<EOF > ${outfile}
<html>
<head>
<title>${title}</title>
</head>
  <h2 align=center>${title}</h2>
EOF
}

entry()
{
    local id=$1
    echo "Processing files for project ${id}..."
    if test -e ${id}-osm.geojson; then
	osmsize=$(grep type -c ${id}-osm.geojson)
    else
	osmsize=0
    fi
    if test -e ${id}-osm.geojson; then
       mssize=$(grep type -c ${id}-ms.geojson)
    else
	mssize=0
    fi
    local path=$(basename $(dirname $PWD))
    path+="/$(basename $PWD)"
    cat <<EOF >> ${outfile}
<ul>
<li>Project ${id}: ${names[${id}]}
<ul>
<li><a href=${id}-osm.geojson>${id}-osm.geojson</a> (${osmsize} buildings)
<li><a href=${id}-ms.geojson>${id}-ms.geojson</a> (${mssize} buildings)
EOF
    if test -e ${id}-buildings.geojson; then
	size=$(grep type -c ${id}-buildings.geojson)
	echo "<li><a href=${id}-buildings.geojson>${id}-buildings.geojson</a> (${size} buildings)" >> ${outfile}
    fi
    cat <<EOF >> ${outfile}    
</ul>
</ul>
EOF
}

direntry()
{
    echo "Processing directory ${1}..."
    file=$1
    if test -e ${file}; then
       size="`du -sh ${file} | grep -o '^[0-9KMG]*'`"
       if test "${size}" = '0'; then
	   return 0
       fi
    fi
    local path=$(basename $(dirname $PWD))
    path+="/$(basename $PWD)"

    local name=$(echo ${file} | cut -d '-' -f 1)
    cat <<EOF >> ${outfile}
    <li><a href=${file}>Project ${name}</a> (${size}), ${names[${id}]}
EOF
}

footer()
{
    local year="$(date '+%Y')"
    cat <<EOF >> ${outfile}
  </dl>
  </ul>
  <p>

  <font size=-2>
    <i>Copyright &copy; ${year} <a href=https://www.hotosm.org</a>OpenStreetMap US</br>
  </font>
 
</body>
</html>
EOF
}

declare -A names

for project in *-project.geojson; do
    id=$(echo ${project} | cut -d '-' -f 1)
    wget https://tasking-manager-tm4-production-api.hotosm.org/api/v2/projects/${id}/queries/summary/ -O ${id}-tmp
    name=$(grep -o '"name": "[^"]*' ${id}-tmp | grep -o '[^"]*$' | grep "^Imagery" | cut -d '-' -f 2)
    names[${id}]="${name}"
    rm -f ${id}-tmp
done

# declare -p names
country="$(basename $PWD)"
header "Tasking Manager Projects in ${country}"

echo "<h2>Tasking Manager Project Boundaries for ${country}</h2>" >> ${outfile}
for project in *-project.geojson; do
    id=$(echo ${project} | cut -d '-' -f 1)
    direntry ${project}
done

echo "<h2>Project Data Files</h2>" >> ${outfile}
for project in *-project.geojson; do
    id=$(echo ${project} | cut -d '-' -f 1)
    entry ${id}
done

footer
