# Conflating External Datasets

This project is the merging of several programs for conflating
external datasets with OpenStreetMap data developed at
[HOT](https://www.hotosm.org). These were originally developed for
large scale building imports using MS Footprints in East Africa, and
to also work with conflating data collected with OpenDataKit for the
[Field Mapping Tasking Manager](https://hotosm.github.io/fmtm/)
project.

## The Data Files

While any name can be used for the OSM database, I usually default to
naming the [OpenStreetMap](http://download.geofabrik.de/index.html)
database the country name as used in the data file. Other datasets
have their own schema, and can be imported with
[ogr2ogr](https://gdal.org/programs/ogr2ogr.html), or using python to
write a custom importer. In that case I name the datbase after the
dataset source. Past versions of this program could conflate between
multiple datasets, so it's good to keep things clear.

## Overture Data

The Overture Foundation (https://www.overturemaps.org) has been
recently formed to build a competitor to Google Maps. The plan is to
use OpenStreetMap (OSM) data as a baselayer, and layer other datasets
on top. The currently available data (July 2023) has 13 different
datasets in addition to the OSM data. It is [available
here](https://overturemaps.org/download/). It also includes a snapshot
 of OSM data from the same time frame. Other than the OSM data and [MS
Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints),
all the current additional data is US specific, and often contains
multiple copies of the same dataset, but from different organization.

The [osm-rawdata](https://hotosm.github.io/osm-rawdata/importer)
python module has a utility that'll import the Parquet data files into
the postgress database schema used by multiple projects at HOT.

### Duplicate Buildings

This is the primary conflation task. Because of offsets in the
satellite imagery used for the original buildings, there is never an
exact duplicate, only similar. The orientation may be different even
if the same rough size, or it'll be roughly in the same position, but
differing sizes. Several checks are made to determine
duplicates. First is to check for any intersection of the two
polygons. This can also be overlapping buildings, so the centroid of
each building polygon is checked to see if they are within each
other. If there is intersection between the buildings but the
centroids aren't within one another, then it's an overlapping building
instead. Any building in the footprint data that is found to be a
duplicate is removed from the output data file.

### Overlapping Buildings

It is entirely possible that a new building in the footprints data may
overlap with an existing building in OSM. It wouldn't be overlapping
in the footprints data. Since this requires human intervention to fix,
these buildings are left in the output data, but flagged with a
debugging tag of *overlapping=yes*.

## Known Problems

There are two main issues with ML/AI derived building footprints,
Buildings that are very close together, like the business section in
many areas of the world, do not get marked as separate
buildings. Instead the entire block of buildings is a single
polygon.

The other problem is that as processing satellite imagery is that
buildings are recognized by shading differences, so often features are
flagged as buildings that don't actually exist. For example, big rocks
in the desert, or haystacks in a field both get marked as a
building. Any building in the footprints data that has no other
buildings nearby, nor a highway or path of some kind is flagged with a
debugging tag of *false=yes*. Usually this is easy to determine
looking at satellite imagery, since there are often remote
buildings. The tags can be searched for when editing the data to
visually determine whether it's a real building or not.

# Output Files

If the data files are huge, it's necessary to conflate with a subset
of all the data. For projects using the [Tasking
Manager](https://tasks.hotosm.org/) or the Field
[Mapping Tasking Manager](https://hotosm.github.io/fmtm/) you can
download the project boundary file and use that. For other projects
you can extract administrative bondaries from OpenStreetMap, or use
external sources. Commonly county administrative boundaries are a good
size. These can be extract from OSM itself, or an external data file
of boundaries.

After conflation, an output file is created with the new buildings
that are not duplicates of existing OSM data. This is much smaller
than the original data, but still too large for anyone having
bandwidth issues. This output file is in
[GeoJson](https://geojson.org/) format, so can be edited with
[JOSM](https://josm.openstreetmap.de) or
[QGIS](https://www.qgis.org/en/site/)

# Validating The Conflation

The conflated data file can't be uploaded to OSM until it is
validated. While QGIS can be used for this purpose, JOSM is preferred
because it does validation checks, and uploads directly to
OpenStreetMap. I start by loading the conflation data file, and then
enabling the OpenStreetMap imagery for the basemap. Existing buildings
in OSM are grey polygons, so it's possible to see existing buildings
with the conflated new buildings as a layer on top.

Once the buildings are loaded, you can then download the OSM data for
that view. Then use the
[SelectDuplicateBuilding](https://github.com/MikeTho16/JOSM-Scripts/blob/master/SelectDuplicateBuilding.js)
script to find any buildings that have been added since the initial
data file for conflation was used. Once selected, those can be
deleted in a single operation.

The next step is validating what is left that is considered to be a
new building. This is done using satellite imagery. Microsoft used
Maxar imagery for their ML/AI model, so I start with that
imagery. Bing should be the same imagery, but I try that next if the
Maxar imagery isn't sufficient. After that I sometimes have to
experiment, or use [Open Aerial Map](https://openaerialmap.org/) to
find something better. Often utilizing multiple fuzzy imagery sources
is necessary, while being concious of the possible false
identification.
