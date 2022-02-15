#!/bin/bash

project=$1

ogr2ogr -s_srs "EPSG:4326" -t_srs "EPSG:4326" -progress -overwrite -f "GeoJSON" ${project}-project.geojson PG:"dbname=tmsnap" -nln "project" -sql "SELECT id AS pid,ST_AsText(geometry) FROM projects WHERE id=${project}"

ogr2ogr -s_srs "EPSG:4326" -t_srs "EPSG:4326" -progress -overwrite -f "GeoJSON" ${project}-tasks.geojson PG:"dbname=tmsnap" -sql "SELECT tasks.id AS tid,projects.id AS pid,ST_AsText(tasks.geometry) FROM tasks,projects WHERE tasks.project_id=${project} AND projects.id=${project}"
