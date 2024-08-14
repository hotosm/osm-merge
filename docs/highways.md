# Conflating Highway and Trail Data

This is focused only on highway and trail data in the US, but should
be useful for other countries. In particular, this is focused on the
primary goal of improving OpenStreetMap data in remote areas as these
are used for emergency response. Most of these roads and trails are in
OSM already, some from past imports, some traced off of satellite imagery. 

I did a talk at SOTM-US in Tucson about this project called
[OSM For Fire
Fighting](https://www.youtube.com/watch?v=qgk9al1rluE). This
conflation software was developed to improve the quality of the remote
highway data in OpenStreetMap. This is not an import of new data, only
updating existing features with a focus on improved
navigation. Importing new features from these datasets uses a
different process, so it's better to not mix the two.

While there are details in the the datasets that would be useful, the
initial set is the name, the reference number, and the vehicle class
appropriate for this highway. Not this can change over time, so if the
*smoothness* tag is in the OSM feature, it's assumed that value is
more accurate.

The primary purpose is to clean up the [TIGER import
mess](https://wiki.openstreetmap.org/wiki/TIGER_fixup), which is often
inaccurate. This leads to navigation problems as sometimes what is in
OSM is not what the street sign says. Since there are multiple
datasets supplied by government agencies with a good license for OSM,
we data mine these through conflation to get the best name and
reference number.

Although most of the fields in these datasets aren't useful for OSM,
some are like is it a seasonal road, various off road vehicle access
permissions, etc... since this is also useful for navigation. Any tags
added or edited will follow the [OSM Tagging
Guidelines](https://wiki.openstreetmap.org/wiki/United_States_roads_tagging#Tagging_Forest_Roads)
for forest roads.

# The Datasets

The primary source of these datasets is available from the 
[FSGeodata Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation),
which is maintained by the [USDA](https://www.usda.gov/).

The Topographical map vector tiles are
[available from
here.](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/),
which is maintained by the National Forest Service.

These have been partially imported in some areas in the past, complete
with the bugs in the original datasets. One big advantage though is
that the geometry in OSM was from the same USDA datasets at some point
in the past, so it's relatively easy to match the
geometries. Conflation then is mostly working through the name and
reference fields between multiple files, which sometimes don't agree
on the proper name.

## Processing The Datasets

Since the files are very large with different schemas, a critical
part of the conflation process is preparing the data. Some of these
files are so large neither QGIS or JOSM can load them without
crashing. I use two primary tools for splitting up the
files. [ogr2ogr](https://gdal.org/programs/ogr2ogr.html) for the
GeoJson files, and [osmium](https://osmcode.org/osmium-tool/) for the
[OSM XML](https://wiki.openstreetmap.org/wiki/OSM_XML) files. The OSM
XML format is required if you want the conflation process to merge the
tags into an existing feature. If conflating with OSM data using the
GeoJson format, you need to manually cut & paste the new tags onto the
existing feature.

As you furthur reduce large datasets to smaller more manageble pieces,
this can generate many files. The top level choice is the largest
category. I use National Forests bopundaries as they can cross state
lines.

All of the datasets have issues with some features lacking a
geometry. These appear to be duplicates of a Feature that does have a
good geometry. They are also in "NAD 83 - EPSG:4269" for the CRS, so
need to convert and fix the geometries. I use *ogr2ogr* to convert the
GDB files to GeoJson like this:

	ogr2ogr Road_MVUM.geojson S_USA_Road_MVUM.gdb.zip -makevalid -s_srs EPSG:4269 -t_srs EPSG:4326 -sql 'SELECT * FROM Road_MVUM WHERE SHAPE IS NOT NULL'

	ogr2ogr Trails_MVUM.geojson S_USA_Trail_MVUM.gdb.zip -makevalid -s_srs EPSG:4269 -t_srs EPSG:4326 -sql 'SELECT * FROM Trail_MVUM WHERE SHAPE IS NOT NULL'

This generates a clean GeoJson file. It has many fields we don't want,
so I run a simple [conversion program](utilities.md) that parses the
fields are defined in the original file, and converts the few fields
we want for conflation into the OSM equivalant tag/value. For
conflation to work really well, all the datasets must use the same
schema for the tags and values.

Since the MVUM dataset covers the entire country, I build a directory
tree in which the deeper you go, the smaller the datasets are. I have
the Nationl Forest Service Administrative boundaries unpacked into a
top level directory. From there I chop the national dataset into just
the data for a forest. This is still a large file, but manageble to
edit. Sometimes with rural highway mapping, a large area works
better. If there are plans to use the [Tasking
Manager](https://tasks.openstreetmap.us/), The files are still too
large, as TM has a 5000sq km limit.

Next is generating the task boundaries for each national forest
that'll be under the 5000km limit. I used the 
[FMTM Splitter](https://hotosm.github.io/fmtm-splitter/) program to
use the national forest boundary and break it into squares, and
clipped properly at the boundary. These task boundary polygons can
then be used to create the project in the Tasking Manager, which will
furthur split that into the size you want for mapping.

Then the real fun starts after the drudgery of getting ready to do
conflation.

### MVUM Roads

This is all the highways in National Forests. The data contains
several fields that wopuld be useful in OSM. This dataset has a
grading of 1-5 for the type of vehicle that can drive the road, as
well as a field for high clearance vehicles only. This is roughly
equivalant to the *smoothness* tag in OSM. The surfce type is also
included, which is the same as the OSM *surface* tag. There are other
fields for seasonal access, and seasonal road closures. Roads tagged
as needing a high clearance vehicle generate a *4wd_only* tag for OSM.

The reference numbers often have a typo, an additional number (often 5
or 7) prefixed to the actual number in the original dataset, and were
imported this way. Since the reference number needs to match what the
map or street sign says, these all need to be fixed. And there are
thousands of these...  

The type of vehicle that can be driven on a particular road is a bit
subjective based on ones off-road driving experience. These are
typically jeep trails of varying quality, but very useful for
backcountry rescues or wildland fires.

### Mvum Trails

These are Multi Vehicle Use Maps (MVUM), which define the class of
vehicle appropriate to drive a road. The trails dataset contains
additional highways, as some hikiing trails are also forest service
roads. These are primarily for hiking, but allow vehicle use,
primarily specialized off-road vehicles like an ATV or UTV. They
suffer from the same bad data as the MVUM roads.

### National Forest Trails

This dataset is hiking trails that don't allow any vehicle usage at
all. Many of these trails are in OSM, but lack the trail name and
reference number. These also get used for emergency response as
well. If there is a name and reference number for the trail, this
makes it easier to refer a location to somebody over a radio instead
of GPS coordinates.

### USGS Topographical maps

It's possible to download the vector datasets used to produce
topographical maps. Each file covers a single 7.5 map quad, which is
49 miles or 78.85 km square. There are two variants for each quad, a
GDB formatted file, and a Shapefile formatted file. The GDB file
contains all the data as layers, whereas the Shapefiles have separate
files for each feature type. I find the smaller feature based files
easier to deal with. The two primary features we want to extract are
**Trans_RoadSegment** and **Trans_TrailSegment**. Because of the
volume of data, I only have a few states downloaded.

I then used *ogrmerge* to produce a single file for each feature from
all the smaller files. This file covers an entire state. This file has
also has many fields we don't need, so only want the same set used for
all the datasets. The
[usgs.py](https://github.com/hotosm/osm-merge/blob/main/utilities/usgs.py)
contained in this project is then run to filter the input data file
into GeoJson with OSM tagging schema. The topographical data is
especially useful for conflation, since the name and reference number
match the paper or GeoPDF maps many people use.
