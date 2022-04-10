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
# These functions are used by the index.sh script
#
outfile="index.html"

header()
{
    local title=$(basename $PWD)
    cat <<EOF >> ${outfile}
<html>
<head>
<title>${title}</title>
</head>
  <h2 align=center>${title}</h2>
EOF
}

mapdir()
{
    local path="$1"
    local idx=0
    local out=""
    
    for file in $(find ${path} -name \*.osm\* -o -name \*.kmz) ; do
	local name="$(basename ${file})"
	# if test x"${file}" = x"*.kmz"; then
	#    local out="no data..."
	#    break
	# fi
	local size="$(stat -c '%s' ${file} ; return $?)"
	if test $? -eq 1; then
	    continue
	fi
	if test ${size} -eq 0; then
	    continue
	fi
	local megs="$(expr ${size} / 1024)"
	if test ${megs} -eq 0; then
	    megs="${size}B"
	else
	    megs="${megs}M"
	fi
	local file=$(echo ${file} | grep -o "/[A-Za-z]*/${name}" | cut -d '/' -f 2-3)
	local index=""
	if test -e ${path}/index.html; then
	    local index=index.html
	fi
	if test ${idx} -eq 0; then
	    local out="<a href=${file}>${name} (${megs})</a>"
	else
	    local out="${out}, <a href=${file}>${name} (${megs})</a>"
	fi
	if test x"${name}" = x"*.bz2"; then
	    local out="<i>No road or trail data</i>."
	fi
	idx=$(expr ${idx} + 1)
    done

    echo ${out}
    if test x"${out}" = x; then
	return 1
    else
	return 0
    fi
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
<li>Project ${id}
<ul>
<li><a href=${path}/${id}-osm.geojson>${id}-osm.geojson</a> (${osmsize} buildings)
<li><a href=${path}/${id}-ms.geojson>${id}-ms.geojson</a> (${mssize} buildings)
EOF
    if test -e ${id}-buildings.geojson; then
	size=$(grep type -c ${id}-ms.geojson)
	echo "<li><a href=${path}/${id}-buildings.geojson>${id}-buildings.geojson</a> (${size} buildings)" >> ${outfile}
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
    <li><a href=${path}/${file}>Project ${name}</a> (${size}, ${file})
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
    <i>Copyright &copy; ${year} <a href=https://www.hotosm.org</a>Humanitarian OpenStreetMap Team</br>
  </font>
 
</body>
</html>
EOF
}

echo "<h2>Tasking Manager Project Boundaries</h2>" >> ${outfile}
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
