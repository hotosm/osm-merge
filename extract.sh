#!/bin/bash

#
# Copyright (C) 2022   Humanitarian OpenStreetMap Team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

#
# This script queries the Tasking Manager database to get the project boundary,
# and the boundaries of all the tasks. Note that when producing GeoJson output,
# the 'id' field gets filtered out by ogr2ogr, so we rename it. Otherwise there
# are no fields in the file used to specify how the large data file gets split.
project=$1

rm -f ${project}-project.geojson
ogr2ogr -s_srs "EPSG:4326" -t_srs "EPSG:4326" -progress -overwrite -f "GeoJSON" ${project}-project.geojson PG:"dbname=tmsnap" -nln "tmproject" -sql "SELECT id AS pid,ST_AsText(geometry) FROM projects WHERE id=${project}"

rm -f ${project}-tasks.geojson
ogr2ogr -s_srs "EPSG:4326" -t_srs "EPSG:4326" -progress -overwrite -f "GeoJSON" ${project}-tasks.geojson PG:"dbname=tmsnap" -nln "tmproject" -sql "SELECT projects.id AS pid,tasks.id AS tid,ST_AsText(tasks.geometry) FROM tasks,projects WHERE tasks.project_id=${project} AND projects.id=${project}"

# ogr2ogr -t_srs "EPSG:4326" -progress -overwrite -f "GeoJSON" regions.geojson PG:"dbname=Nigeria" -sql "SELECT name,wkb_geometry FROM multipolygons WHERE boundary='administrative' AND admin_level='4'"
