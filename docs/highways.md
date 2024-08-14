# Conflating Highway and Trail Data

This is focused only on highway and trail data in the US, but should
be useful for other countries. In particular, this is focused on the
primary goal of improving OpenStreetMap data in remote areas, as these
are used for emergency response. Most of these roads and trails are in
OSM, some from past imports, some traced off of satellite imagery. 

I did a talk at SOTM-US in Tucson about this project called
[OSM For Fire
Fighting](https://www.youtube.com/watch?v=qgk9al1rluE). This
conflation software was developed to improve the quality o f the remote
highway data in OpenStreetMap. This is not an import of new data, only
updating existing features with a focus on improved
navigation. Importing new features from these datasets uses a
different process, so it's better to not mix the two.

While there are details in the the datasets that would be useful, the
initial set is the name, the reference number, and the vehicle class
appropriate for this highway. Not this can change over time, so if the
*smoothness* tag is in the OSM feature, it's assumed that value is
more accurate.

# The Datasets

The primary source of these datasets is available from the 
[FSGeodata Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation),
which is maintained by the [USDA](https://www.usda.gov/).

The Topographical map vector tiles are
[available from
here.](https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/),
which is maintained by the National Forest Service.

## Processing The Datasets

Since the files are very large with different schemas, a critical
part of the conflation process is preparing the data. Some of these
files are so large neither QGIS or JOSM can load them without
crashing. I use two primary tools for splitting up the
files. [ogr2ogr](https://gdal.org/programs/ogr2ogr.html) for the
GeoJson files, and [osmium](https://osmcode.org/osmium-tool/) for the
[OSM XML](https://wiki.openstreetmap.org/wiki/OSM_XML) files. The OSM
XML format is required if you want the conflation process to merge the
tags into an existing feature. If conflating with OSM data uding the
GeoJson format, you need to manually cut & paste the new tags onto the
existing feature.

As you furthur reduce large datasets to smaller more manageble pieces,
this can generate many files. The top level choice is the largest
category. I use National Forests, they can cross state boundaries
though so you can't use state boundaries anymore.

## MVUM Roads

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
thousands of these...  This is a bit subjective based on
ones off-road driving experience. These are typically jeep trails of
varying quality, but very useful for backcountry rescues or wildland
fires.

## Mvum Trails

These are Multi Vehicle Use Maps (MVUM), which define the class of
vehicle appropriate to drive a road. The trails dataset contains
additional highways, as some hikiiing trails are also forest service
roads. These are primarily for hiking, but allow vehicle use,
primarily specialized off-road vehicles like an ATV or UTV.

## National Forest Trails

This dataset is hiking trails that don't allow any vehicle usage at
all. Many of these trails are in OSM, but lack the trail name and
reference number. These also get used for emergency response as well.

## USGS Topographical maps

It's possible to download the vector datasets used to produce
topographical maps. Each file covers a single 7.5 map quad, which is
49 miles or 78.85 km square. There are to variants for each qud, a GDB
formatted file, and a Shapefile formatted file. The GDB file contains
all the data as layers, whereas the Shapefiles have separate files for
each feature type. I find the smaller feature based files easier to
deal with. The two primary features we want to extract are 
**Trans_RoadSegment** and **Trans_TrailSegment**. Because of the
volumne of data, I only have a few states downloaded.

I then used *ogrmerge* to produce a single file for each feature from
all the smaller files. This file covers an entire state. This file has
many fields we don't need, so only want the same set used for all the
datasets. The
[usgs.py](https://github.com/hotosm/osm-merge/blob/main/utilities/usgs.py)
contained in this project is then run to filter the input data file
into GeoJson. The topographical data is especially useful for
conflation, since the name a reference numbers match the paper or
GeoPDF maps many people use.

[OSM Tagging Guidelines](https://wiki.openstreetmap.org/wiki/United_States_roads_tagging#Tagging_Forest_Roads)
