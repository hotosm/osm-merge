# TM Splitter Utility

This program manages tasks splitting and data extraction. Since we're
dealing with very large files, being able to chop them into manageable
pieces is critical. For remote mapping using satellite or drone
imagery, many use the [HOT Tasking
Manager](https://tasks.hotosm.org) (TM). This will let you create a
project which the TM will then split into tasks for the mappers.

The tm-splitter program is a command line utility to do the same
thing, but is focused on processing large files for imports or
conflation. This is also designed to work with the TM, pre-processing
data for a TM project so the mapper can focus on validation.

If could also be used in the backed for other Tasking Manager style
projects as it uses an object oriented approach. The command line
version is just more useful for development.

# Task Splitting

This will split a large Area Of Interest (AOI) into a grid of
tasks. The TM has a 5000km sq limit, and all of our data files are
much larger. Initially this can be used to chop the large area into
4999km sq tasks. The best threshold option for this size task is
*0.7*. That's what is used to create the project AOI for the TM
project. 

While it's entirely possible to let TM split the tasks for the
project, I've found when dealing with data extracts it's better to
generate our small tasks outside of TM. TM will let us upload a custom
task grid. Since this project is focused on trails and MVUM
linestrings in remote areas, larger tasks work better than small ones
as the density of features in each task square is low. I've been using
*0.1* as the threshold value for that size, although slightly larger
might be better.

# Data Extraction

While there are a multitude of options for extracting data from
OpenStreetMap (OSM), this is more focused on chopping up the initial
data extract into the smaller task sized pieces. It turns out there
are issues when making data extracts of highways that you want to
conflate. In the OSM world, [osmium](https://osmcode.org/osmium-tool/)
and [osmconvert](https://osmcode.org/osmium-tool/) when clipping data,
highways that cross the boundary and extend outside are completed,
instead of being clipped at the boundary. This avoids all sorts of
problems with bad references, missing nodes, etc...

The problem though was with external datasets. Using
[ogr2ogr](https://gdal.org/programs/ogr2ogr.html) for clipping the NPS
trail data, or the USDA MVUM datasets clips everything at the
boundary, and of course other OSM tools can't be used with GeoJson
files. TM Splitter has support to clip the data extract at the
boundary, but to also extend all linestrings that cross the boundary
to be complete. This way the geometrys are more likely to be similar
between OSM and the external datasets, which helps with conflation.

When conflating, there are issues when you get near the boundary. With
large datasets, you won't see any problems except at those
intersections. But as you reduce the size of your tasks towards a
*0.1* threshold, there starts to be issues with incomplete features
which is why extending the linestrings helps.

It's also possible to conflate the larger datasets and then generate
the smaller task sized data extracts by splitting the post-conflated
data. That's probably more of a normal mode of mapper data flow. But
the smallest tasks are very useful for debugging and fine tuning the
conflation algorithm.

# Tasking Manager Integration

The HOT Tasking Manager is focused on remote mapping using imagery, so
has a few additional functions we don't really need. For one thing, a
TM project assumes you are using imagery, it's part of the project
profile. So when you select a task to map, it'll load the imagery into
the [JOSM](https://josm.openstreetmap.de/) or
[iD](https://www.openstreetmap.org/edit?editor=id) editors. We don't
really need the imagery as we're not modifying the geometry, just the
metadata of each feature. For the OSM Merge project, we use
topographical map as a basemap, not satellite imagery.

# Options

Usage: tm-splitter [-h] [-v] -i INFILE [-g] [-s] [-o OUTFILE] [-e EXTRACT] [-c] [-t THRESHOLD]

options:
  -h, --help                             show this help message and exit
  -v, --verbose                          verbose output
  -c, --complete                         Complete all LineStrings
  -g, --grid                             Generate the task grid
  -s, --split                            Split Multipolygon
  -i INFILE, --infile INFILE             The input dataset
  -o OUTFILE, --outfile OUTFILE          Output filename
  -e EXTRACT, --extract EXTRACT          Split Dataset with Multipolygon
  -t THRESHOLD, --threshold THRESHOLD    Threshold

This program implements some HOT Tasking Manager style functions
for use in other programs. This can generate a grid of tasks from an
AOI, and it can also split the Multipolygon of that grid into separate
files to use for clipping with ogr2ogr.

To break up a large public land boundary, a threshold of 0.7 gives
us a grid of just under 5000 sq km, which is the TM limit.

	tm-splitter.py -v --grid --infile boundary.geojson --threshold 0.7

To split the grid file file into tasks, this will generate a separate
file for each polygon within the grid. This file can then also be used
for clipping with other tools like ogr2ogr, osmium, or osmconvert.

	tm-splitter.py -v --split --infile tasks.geojson

	tm-splitter.py -v --split --infile tasks.geojson

This will split the data extract into a task sized chunk, one for each
polygon in the boundary file. All linestrings are completed to avoid
problems with conflation.
        
	tm-splitter.py -v --complete -i infile.geojson -e boundary.geojson
