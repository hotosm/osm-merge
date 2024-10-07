#!/bin/bash

# Copyright (C) 2024 Humanitarian OpenstreetMap Team
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

# This script processes multiple boundaries to create the data extracts
# for every task being setup for the HOT Tasking Manager.

states="Utah Colorado Wyoming"

# Top level for boundaries, obviously system specific
boundaries="/play/MapData/Boundaries/"

# The base datasets
osmdata="../wy-co-ut.osm.pbf"
mvumhighways="../Road_MVUM-out.geojson"
mvumtrails="../Trail_MVUM-out.geojson"
topohighways="../USGS_Topo_Roads-out.geojson"
topotrails="../USGS_Topo_Trails-out.geojson"
npstrails="../National_Park_Service_Trails-out.geojson"
usfstrails="../USFS_Trails-out.geojson"

utah="Dixie_National_Forest \
      Bryce_Canyon_National_Park \
      Zion_National_Park \
      Capitol_Reef_National_Park \
      Arches_National_Park \
      Manti_La_Sal_National_Forest \
      Canyonlands_National_Park \
      Uinta_Wasatch_Cache_National_Forest \
      Fishlake_National_Forest \
      Ashley_National_Forest"

colorado="Arapaho_and_Roosevelt_National_Forests \
          Medicine_Bow_Routt_National_Forest \
          Grand_Mesa_Uncompahgre_and_Gunnison_National_Forests \
          Rio_Grande_National_Forest \
          San_Juan_National_Forest \
          Rocky_Mountain_National_Park"

wyoming="Bighorn_National_Forest \
         Bridger_Teton_National_Forest \
         Ashley_National_Forest \
         Caribou_Targhee_National_Forest \
         Shoshone_National_Forest \
         Black_Hills_National_Forest \
         Yellowstone_National_Park \
         Grand_Teton_National_Park"

# FIXME: figure why this isn't accessible in a bash function
declare -gA datasets
datasets["Utah"]="${utah}"
datasets["Colorado"]="${colorado}"
datasets["Wyoming"]="${wyoming}"

# declare -p ${datasets}

# Debugging help
dryrun="" # echo

# FIXME: script in the utilities directory don't get install by pip
root="${HOME}/projects/HOT/osm-merge.git"
# The git branch, usually main except when debugging
branch="main"
# fixnames="${dryrun} ${root}/${branch}/osm_merge/utilities/fixnames.py"
tmsplitter="${dryrun} ${root}/${branch}/osm_merge/utilities/tm-splitter.py"
osmhighways="${dryrun} ${root}/${branch}/osm_merge/utilities/osmhighways.py"

ogropts="${dryrun} ogr2ogr -t_srs EPSG:4326 -makevalid -explodecollections -nlt LINESTRING -clipsrc"
osmopts="${dryrun} osmium extract -s smart --overwrite --polygon "
osmconvert="osmconvert --complete-ways --drop-broken-refs -B="

get_task_num() {
    # Extract the task number from the file name.
    task="${1}"
    num=$(echo ${task} | grep -o "[0-9]*")
    if test x"${num}" = x; then
	# Top level forest or parks don't have a task number
	echo ""
    fi
    echo "Tasks_${num}"

    return 0
}

get_subtask_num() {
    # Extract the 2 task numbers from the file name.
    task="${1:?}"
    nums=$(echo ${task} | grep -o "[0-9]*[0-9]*" | tr '\n' '_')
    length=$(expr $(echo ${#nums} - 1))
    if test ${length} -lt 0; then
       echo ""
    else
	subnum="${nums:0:${length}}"
	echo "SubTask_${subnum}"
    fi

    return 0
}

get_dirname() {
    # Extract the directory name from the filename.
    file="${1:?}"
    dir=$(echo ${file} | cut -d '.' -f 1)
    echo ${dir}

    return 0
}

get_short_name() {
    # Drop the National_Forest or National_Park part of the path
    name="${1:?}"
    short=$(basename ${name} | sed -e "s/_National_Forest//" -e "s/National_Park//" -e "s/Tasks/Task/")
    echo ${short}

    return 0
}

extract_data() {
    clipsrc="${1:?}"
    intype="${2:?}"
    # outfile="${3:?}"

    type=""
    if test $(echo ${clipsrc} | grep -c "[0-9]*") -gt 0; then
	# It's a Task boundary
	type="task"
    else
	# It's a forest or park boundary
	type="land"
    fi
    if test x"${type}" = x; then
	echo "ERROR: bad filespec!"
	return 1
    fi

    dataset=""
    if test $(echo ${indata} | grep -c "MVUM") -gt 0; then
	# It's the MVUM dataset
	dataset="MVUM"
    else
	# It's the OSM dataset
	dataset="OSM"
    fi
    if test x"${dataset}" = x; then
	echo "ERROR: bad filespec!"
	return 1
    fi

    for task in ${clipsrc}; do
	echo "    Extracting data from ${dataset} task ${task} ..."
	num=$(get_task_num ${task})
	subnum=$(get_subtask_num ${task})
	dirname=$(dirname ${task})
	outfile="${dirname}/${dataset}_Highways_${num}"
	short=$(get_short_name ${task})
	case ${intype} in
	    OSM_Highways)
		case ${type} in
		    task)
			indata="${dirname}/*_OSM_Highways.osm"
		    ;;
		    land)
			indata="${osmdata}"
		    ;;
		esac
		# ${osmhighways} --clip ${task} -v -o ${outfile}.osm -i ${indata}
		${osmconvert}${task} -v ${indata} > ${outfile}.osm
	    ;;
	    MVUM_Highways)
		case ${type} in
		    task)
			indata="${dirname}/${num}.geojson"
		    ;;
		    land)
			indata="${mvumhighways}"
		    ;;
		esac
		outfile="${outfile}.geojson"
		echo ${ogropts}
	    ;;
	esac

	# if test x"${poly}" = x; then
	#     echo "ERROR: bad boundary!"
	#     return 1
	# fi

	if test ! -e ${indata}; then
	    echo "ERROR: ${indata} does not exist!"
	    return 1
	fi

    done

    return 0
}

split_aoi() {
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:all}"
    tmmax=70000
    for state in ${region}; do
	echo "Splitting ${state} into squares with ${tmmax} per side"
	for land in ${datasets["${state}"]}; do
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    if test x"${dataset}" != x -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    echo "    Making TM sized projects for ${land}"
	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		aoi="${boundaries}/NationalParks/${land}.geojson"
	    else
		aoi="${boundaries}/NationalForests/${land}.geojson"
	    fi
	    # fmtm-splitter -v -b ${aoi} -m ${tmmax}
	    # This generates a grid of roughly 5000sq km tasks,
	    # which is the maximum TM supports. Some areas are
	    # smaller than this, so only one polygon.
	    ${tmsplitter} --grid --infile ${aoi} --threshold 0.7
	    # Make a multipolygon even if just one task
	    ${ogropts} -clipsrc ${aoi} ${base}_Tasks.geojson output.geojson
	    rm -f output.geojson
	    echo "Wrote ${base}_Tasks.geojson"
	done
    done
}

make_tasks() {
    # Split the multipolygon from tm-splitter into indivigual files
    # for ogr2ogr and osmium.
    # $1 is an optional state to be the only one processed
    # $2 is an optional national forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:all}"
    for state in ${region}; do
	echo "Making task boundaries for for ${state}..."
	for land in ${datasets["${state}"]}; do
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    short=$(get_short_name ${base})
	    if test x"${dataset}" != x -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    if test ! -e ${dir}; then
		mkdir ${dir}
	    fi
	    echo "    Making task boundaries for clipping to ${land}"
	    ${tmsplitter} -v -s -i ${base}_Task.geojson -o ${dir}
	    tasks=${dir}/${short}_Task_*.geojson
	    for task in ${tasks}; do
		num=$(get_task_num ${task})
		short=$(get_short_name ${task})
		# mv -f ${base}_${num}.geojson ${dir}/${short}
	     	echo "Wrote task ${dir}/${short} ..."
	    done
	done
    done
}

make_sub_tasks() {
    # Split the polygon of the task into smaller sizes, each to fit
    # a small TM task. These are used to make small task sized
    # data extracts of the post conflated data to avoid lots of
    # cut & paste.
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:all}"
    for state in ${region}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    echo "    Making task boundaries for clipping to ${land}"
	    short=$(get_short_name ${land})
	    tasks=${dir}/${short}_Task_*.geojson
	    for task in ${tasks}; do
		num=$(echo ${task} | grep -o "Tasks_[0-9]*")
		base=$(echo ${task} | cut -d '.' -f 1)
		if test ! -e ${base}; then
		    mkdir -p ${base}
		fi
		echo "    Making sub task boundaries for ${task}"
		${tmsplitter} --grid --infile ${task} --threshold 0.1

		# Clip to the boundary
		${ogropts} -clipsrc ${task} ${base}/${short}_Tasks.geojson output.geojson
		${tmsplitter} -v --split --infile ${base}/${short}_Tasks.geojson
		# for sub in ${base}/${short}*; do
		#     subnum=$(get_subtask_num ${sub})
		#     echo "Making sub task OSM boundary for $(basename ${sub})"
		#     out=$(echo ${sub} | sed -e "s/_Task_/_OSM_Task_/" | cut -d '.' -f 1)

		#     # rm -f ${base}/${land}/tmp.geojson
		# done
	    done
	done
    done
}

make_sub_mvum() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional national forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"    
    for state in ${region}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    echo "    Making task boundaries for clipping to ${land}"
	    for task in ${state}/${land}_Tasks/${land}*_Tasks*.geojson; do
		${ogropts} -clipsrc ${task} ${state}/${land}_Tasks/${land}_MVUM_${num}.geojson ${state}/${land}_Tasks/mvum.geojson
		dir=$(echo ${task} | cut -d '.' -f 1)
		num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		short=$(get_short_name ${task})
		for sub in ${dir}/${short}Task*; do
		    subnum=$(echo ${sub} | grep -o "Task_[0-9]*_Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		    echo "Making sub task MVUM extract for $(basename ${sub})"
		    out=$(echo ${sub} | sed -e "s/_Task_/_MVUM_Task_/")
		    ${ogropts} -clipsrc ${sub} ${out} ${state}/${land}_Tasks/${land}_MVUM_${num}.geojson
		done
	    done
	done
    done
}

make_sub_osm() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"    
    # Make the data extract for the public land from OSM
    for state in ${region}; do
	echo "Processing public lands in ${state}..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    echo "    Making task boundaries for clipping to ${land}"
	    short=$(get_short_name ${land})
	    tasks=$(find ${dir} -type d)
	    for dir in ${tasks}; do
		extract_data "${dir}/${short}_Tasks_*.geojson" OSM_Highways
	    done
	    # 	${osmhighways} -v --clip ${task} -o ${base}_OSM_${num}.osm -i ${base}_OSM_Highways.osm
	    # 	# ${osmopts} --polygon ${task} -o ${base}_OSM_${num}.osm ${base}_OSM_Highways.osm
	    # 	dir=$(echo ${task} | cut -d '.' -f 1)
	    # 	num=$(echo ${task} | grep -o "Tasks_[0-9]*")
	    # 	# Drop the National_Forest part of the path
	    # 	short=$(get_short_name ${task})
	    # 	subtasks=${base}_${num}/*Tasks*
	    # 	# for sub in ${subtasks}; do
	    # 	#     subnum=$(echo ${sub} | grep -o "Tasks_[0-9]*_Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
	    # 	#     echo "Making sub task OSM extract for $(basename ${sub})"
	    # 	#     out=$(echo ${sub} | sed -e "s/_Tasks_/_OSM_Tasks_/" | cut -d '.' -f 1)
	    # 	#     # ${osmopts} --polygon ${sub} -o ${out}.osm ${base}_OSM_Highways_${num}.osm
	    # 	# done
	    # done
	done
    done
}

make_nps_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    base="${1-yes}"
    tasks="${2-yes}"
    # Make the data extract from the NPS Trail data
    for state in ${states}; do
     	echo "Processing NPS data in ${state}..."
     	for land in ${datasets["${state}"]}; do
	    if test $(echo ${land} | grep -c "_Forest" ) -gt 0; then
		continue
	    fi
	    if test x"${base}" == x"yes"; then
		echo "    Making ${land}_NPS_Trails.geojson"
		rm -f ${state}/${land}_Tasks/${land}_NPS_Trails.geojson
		${ogropts} -clipsrc ${boundaries}/NationalParks/${land}.geojson ${state}/${land}_Tasks/${land}_NPS_Trails.geojson ${npstrails}
	    fi

	    if test x"${tasks}" == x"yes"; then
		for task in ${state}/${land}_Tasks/*_Tasks*.geojson; do
		    echo "    Processing NPS task ${task}..."
		    num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		    rm -f ${state}/${land}_Tasks/${land}_NPS_${num}.geojson
		    ${ogropts} \
			      -clipsrc ${task} ${state}/${land}_Tasks/${land}_NPS_${num}.geojson \
			      ${state}/${land}_Tasks/${land}_NPS_Trails.geojson
		done
	    fi
    	done
    done
}

make_topo_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    base="${1-yes}"
    tasks="${2-yes}"
    for state in ${states}; do
     	echo "Processing Topo data in ${state}..."
     	for land in ${datasets["${state}"]}; do
     	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		clip="NationalParks"
	    else
		clip="NationalForests"
	    fi
	    if test x"${base}" == x"yes"; then
		echo "    Making ${land}_NPS_Trails.geojson"
		rm -f ${forest}_Tasks/${land}_Topo_Trails.geojson
		# ${ogropts} -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_USGS_Topo_Roads.geojson ${topotrails}
		${tmsplitter} -v -e ${boundaries}/${clip}/${land}.geojson -o ${state}/${land}_Tasks/${land}_USGS_Topo_Roads.geojson -i ${topotrails}

		rm -f ${forest}_Tasks/${land}_Topo_Trails.geojson
		# ${ogropts} -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_USGS_Topo_Trails.geojson ${topohighways}
		${tmsplitter} -v -e ${boundaries}/${clip}/${land}.geojson -o ${state}/${land}_Tasks/${land}_USGS_Topo_Trails.geojson -i ${topohighways}
	    fi

	    if test x"${tasks}" == x"yes"; then
		for task in ${state}/${land}_Tasks/*_Tasks*.geojson; do
		    echo "    Processing Topo task ${task}..."
		    num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		    rm -f ${state}/${land}_Tasks/${land}_USGS_Topo_${num}.geojson
		    # ${ogropts} -clipsrc ${task} ${state}/${land}_Tasks/${land}_USGS_Topo_${num}.geojson ${state}/${land}_Tasks/${land}_USGS_Topo_Roads.geojson
		    ${tmsplitter} -v -e ${task} -o ${state}/${land}_Tasks/${land}_USGS_Topo_${num}.geojson -i ${state}/${land}_Tasks/${land}_USGS_Topo_Roads.geojson
		done
	    fi
    	done
    done
}

make_sub_nps() {
    echo "make_sub_nps() unimplemented"
}

make_sub_topo() {
    echo "make_sub_topo() unimplemented"
}

make_mvum_extract() {
    # Make the data extract for the public land from MVUM
    # $1 is whether to make the huge data extract for all tasks
    # $2 is whether to make smaller task extracts from the big one
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    # base=${3:-no}
    base="yes"
    # tasks=${4:-no}
    tasks="yes"
    for state in ${region}; do
     	echo "Processing MVUM data in ${state}..."
     	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
     	    if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		clip="NationalParks"
	    else
		clip="NationalForests"
	    fi
	    if test x"${base}" == x"yes"; then
		rm -f ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
		echo "    Making ${land}_MVUM_Roads.geojson"
		${ogropts} ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson ${mvumhighways}
		# ${tmsplitter} -v -complete -e ${boundaries}/${clip}/${land}.geojson -o ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson -i ${mvumhighways}

		echo "    Making ${land}_MVUM_Trails.geojson"
		rm -f ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson
		# ${ogropts} -clipsrc ${boundaries}/${clip}/${land}.geojson ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson ${mvumtrails}
		${tmsplitter} -v -complete -e ${boundaries}/${clip}/${land}.geojson -i ${state}/${land}_Tasks/${land}_MVUM_Trails.geojson -i ${mvumtrails}

		# Merge the MVUM roads and trails together, since in OSM they
		# are both in the data extract used for vconflation.
		# echo "    Merging MVUM Trails and Roads together"
		# rm -f ${state}/${land}_Tasks/mvum.geojson
		# ${dryrun} ogrmerge.py -nln mvum -o ${state}/${land}_Tasks/mvum.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
		# ${dryrun} ogrmerge.py -nln mvum -append -o ${state}/${land}_Tasks/mvum.geojson ${state}/${land}_Tasks/${land}_MVUM_Roads.geojson
	    fi

	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    tasks="${dir}/*_Task_*.geojson"
	    for task in ${tasks}; do
		echo "    Processing MVUM task ${task} ..."
		num=$(echo ${task} | grep -o "Tasks_[0-9]*" | sed -e "s/Tasks/Task/")
		# ${ogropts} -clipsrc ${task} ${state}/${land}_Tasks/${land}_MVUM_${num}.geojson ${state}/${land}_Tasks/mvum.geojson
		${tmsplitter} -v -complete -e ${task} -o ${state}/${land}_Tasks/${land}_MVUM_${num}.geojson -i ${mvumhighways}
	    done
    	done
    done
}

make_osm_extract() {
    # Make the data extract for the public land from OSM
    # $1 is an optional state to be the only one processed
    # $2 is an optional nartional forest or park to be the only one processed
    # These are mostly useful for debugging, by default everything is processed
    region="${1:-${states}}"
    dataset="${2:-all}"
    # base=${3:-no}
    basedata="no" # this makes the base dataset for the forest or park
    # tasks=${4:-no}
    tasks="yes"
    # Clipping is not done on state boundaries since National Forests often
    # cross state lines.
    for state in ${region}; do
	echo "Extracting ${state} public lands from OSM..."
	for land in ${datasets["${state}"]}; do
	    if test x"${dataset}" != x"all" -a x"${dataset}" != x"${land}"; then
	       continue
	    fi
	    dir="${state}/${land}_Tasks"
	    base="${dir}/${land}"
	    # if test ! -e ${base}_Tasks; then
	    # 	mkdir -p ${state}/${land}_Tasks
	    # fi
	    if test x"${basedata}" == x"yes"; then
		# echo "    Clipping OSM data for ${land}..."
		if test $(echo ${land} | grep -c "_Park" ) -gt 0; then
		    ${osmhighways} -v --clip ${boundaries}/NationalParks/${land}.geojson -o ${base}_OSM_Highways.osm -i ${osmdata}
		    # ${osmopts} --polygon ${boundaries}/NationalParks/${land}.geojson -o ${base}_OSM_Highways.osm ${osmdata}
		else
		    ${osmhighways} -v --clip ${boundaries}/NationalForests/${land}.geojson -o ${base}_OSM_Highways.osm -i ${osmdata}
		    # ${osmopts} --polygon ${boundaries}/NationalForests/${land}.geojson -o ${base}_OSM_Highways.osm  ${osmdata}
		fi
		# Fix the names & refs in the OSM data
		# ${dryrun} ${fixnames} -v -i ${base}_OSM_Highways.osm
		# ${dryrun} mv out-out.osm ${base}_OSM_Highways.osm
	    fi

	    # tasks=${base}*_Tasks_*.geojson
	    extract_data "${dir}/*_Task_*.geojson" OSM_Highways
	done
    done
}

make_baseset() {
    declare -A datasets
    datasets["Utah"]="${utah}"
    datasets["Colorado"]="${colorado}"
    datasets["Wyoming"]="${wyoming}"
  
    for base in ${states}; do
	echo "Processing ${base} public lands..."
	for land in ${datasets["${base}"]}; do
	    echo "    Making baseset for ${land}"
	    for file in ${source}; do
		rm -f ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson
		echo ${ogropts} -clipsrc ${forest}.geojson ${forest}_Tasks/${forest}_USFS_MVUM_Roads.geojson /play/MapData/SourceData/Road_MVUM-out.geojson
		echo $file
	    done
	done
    done	
}

fixnames() {
    # Fix the OSM names
    osm=$(find -name \*.osm)
    for area in ${osm}; do
	${fixnames} -v -i ${area}
    done
}

clean_tasks() {
    files=$(find -name \*_Tasks_[0-9]*.geojson)
    # echo ${files}
    rm -f ${files}
}

usage() {
    echo "This program builds all the smaller datasets from the"
    echo "larger source datasets."
    echo "--tasks (-t): Split tasks boundaries into files for ogr2ogr"
    echo "--base (-b): build all base datasets, which is slow"
    echo "--forests (-f): Build only the National Forests"
    echo "--datasets (-d): Build only this dataset for all boundaries"
    echo "--split (-s): Split the AOI into tasks, also very slow"
    echo "--extract (-e): Make a data extract from OSM"
    echo "--only (-o): Only process one state"
    echo "--dryrun (-n): Don't actually write any datafiles"
    echo "--clean (-c): Remove generated task files"
}

if test $# -eq 0; then
    usage
    exit
fi

# To speciofy a single state and/or forest or park, the -o and -d
# options must be before the actions.
while test $# -gt 0; do
    case "$1" in
	-h|--help)
	    usage
	    exit 0
	    ;;
	-n|--dryrun)
	    dryrun="echo"
	    ;;
	-b|--base)
	    basedata="yes"
	    # make_baseset
	    break
	    ;;
	-o|--only)
	    shift
	    region=$1
	    ;;
	-s|--split)
	    split_aoi ${region} ${dataset}
	    break
	    ;;
	-d|--datasets)
	    shift
	    dataset=$1
	    ;;
	-t|--tasks)
	    # make_tasks ${region} ${dataset}
	    make_sub_tasks ${region} ${dataset}
	    break
	    ;;
	-f|--forests)
	    make_sub_mvum
	    break
	    # process_forests
	    ;;
	-c|--clean)
	    clean_tasks
	    break
	    ;;
	-e|--extract)
	    # This may run for a long time.
	    # make_osm_extract ${region} ${dataset} ${basedata}
	    # make_sub_osm ${region} ${dataset} ${basedata}
	    make_mvum_extract ${region} ${dataset} ${basedata}
	    # make_sub_mvum ${region} ${dataset} ${basedata}
	    # make_nps_extract ${region} ${dataset} ${basedata}
	    # make_sub_nps ${region} ${dataset} ${basedata}
	    # make_topo_extract ${region} ${dataset} ${basedata}
	    # make_sub_topo ${region} ${dataset} ${basedata}
	    break
	    ;;
	-a|--all)
	    # The kitchen sink, do everything
	    split_aoi
	    make_tasks
	    make_sub_tasks
	    make_osm_extract ${basesets} yes
	    make_sub_osm ${basesets} yes
	    make_mvum_extract ${basesets} yes
	    make_sub_mvum
	    make_nps_extract
	    make_sub_nps
	    make_topo_extract
	    make_sub_topo
	    break
	    ;;
	-w)
	    make_nps_extract
	    make_topo_extract
	    ;;
	*)
	    # process_forests
	    # process_parks
	    ;;
    esac
    shift
done
