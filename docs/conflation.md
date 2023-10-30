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
write a custom importer. In that case I name the database after the
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
all the current additional data is primarily US specific, and often
contains multiple copies of the same dataset, but from different
organization.

The [osm-rawdata](https://hotosm.github.io/osm-rawdata/importer)
python module has a utility that'll import the Parquet data files into
the postgress database schema used by multiple projects at HOT. That
schema is designed for data analysis, unlike the standard OSM database
schema. There is more detail in these notes I've written about
importing
[Overture Data](https://hotosm.github.io/osm-rawdata/overture/) into
postgres.

### Duplicate Buildings

This is the primary conflation task. Because of offsets in the
satellite imagery used for the original buildings, there is rarely an
exact duplicate, only similar. The only times when you see an exact
duplicate, it's because the same source data is in multiple other datasets.
The orientation may be different even if the same rough size, or it'll
be roughly in the same position, but differing sizes. Several checks
are made to determine duplicates. First is to check for any
intersection of the two polygons. If the two polygons intersection
it's an overlapping building or possibly duplicate. Any building in
the footprint data that is found to be a duplicate is removed from the
output data file.

### Overlapping Buildings

It is entirely possible that a new building in the footprints data may
overlap with an existing building in OSM. It wouldn't be overlapping
in the footprints data. Since this requires human intervention to fix,
these buildings are left in the output data, but flagged with a
debugging tag of *overlapping=yes*. There is also many occurances
where the building being imported has a better building geometry than
OSM, so the best one should be selected.

Using the HOT [Underpass](https://github.com/hotosm/underpass/wiki)
project, it is possible to scan the building geometries and either
delete the bad geometry one, or flag it in the result data files for a
human to validate the results.

## Known Problems

There are two main issues with ML/AI derived building footprints,
Buildings that are very close together, like the business section in
many areas of the world, do not get marked as separate
buildings. Instead the entire block of buildings is a single
polygon. This will eventually get fixed by drone mapping, where there
can be more of a street view of the buildings that you can't get using
existing satellite imagery.

The other problem is that as processing satellite imagery is that
buildings are recognized by shading differences, so often features are
flagged as buildings that don't actually exist. For example, big rocks
in the desert, or haystacks in a field both get marked as a
building. Any building in the footprints data that has no other
buildings nearby, nor a highway or path of some kind, is flagged with
a debugging tag of *false=yes*. Usually this is easy to determine
looking at satellite imagery, since these are often remote
buildings. The tags can be searched for when editing the data to
visually determine whether it's a real building or not.

# Conflating Other Than Buildings

## OpenDataKit

Data collected in the field using ODK Collect is a specific case. If
using using data extracts from OpenStreetMap, the data extract has
the OSM ID, so it's much simpler to conflate the new tags with either
the existing building polygon or POI. For this workflow, any tag in
the feature from ODK will overwrite any existing values in the
existing feature. This allows for updating the tags & values when
ground-truthing. When the OSM XML file is loaded into JOSM, it has the
*modified* attribute set, and the version has been incremented. In
JOSM under the **File** menu, select the **Update Modified** menu
item. This will sync the modified feature with current OSM. At that
point all that needs to be done is validate the modified features, and
upload to OSM.

When ODK Collect is used but has no data extract, conflation is more
complicated. For this use case, a more brute force algorythm is
used. Initially any building polygon or POI within 7 meters is found
by querying the database. Most smartphone GPS chipsets, even on
high-end phones, are between 4-9m off from your actual location. That
value was derived by looking at lots of data, and can be changed when
invoking the conflation software in this project. Once nearby
buildings are identified, then the tags are compared to see if there
is a match.

For example, if collecting data on a restaurant, it may have a new
name, but if the nearby building is the only one with an
*amenity=restaurant** (or cafe, pub, etc...) it's considered a
probable match. If there are multiple restaurants this doesn't work
very well unless the name hasn't changed. If there are multiple
possible features, a *fixme=* tag is added to the POI, and it has to
be later validated manually. Every tag in the ODK data has to be
compares with the nearby buildings. Often it's the *name* tag that is
used for many amenities.

If a satellite imagery basemap is used in Collect, conflation is
somewhat simpler. If the mapper has selected the center of the
building using the basemap, conflation starts by checking for the
building polygon in OSM that contains this location. If no building is
found, the POI is added to the output file with a *fixme=new building*
tag so the buildings can traced by the validator. Any tags from the
POI are added to the new building polygon.

## Points Of Interest (POI)

It is common when collecting datasets from non-OSM sources each
feature may only be single node. This may be a list of schools,
businesses, etc... with additional information with each POI that can
be added to the OSM building polygon (if it exists). Obviously any
imported data must have a license acceptable for importing into OSM.

Similar to how conflating ODK data when not using a data extract, the
tags & values are compared with any nearby building. Since often these
imports are features already in OSM with limited metadata, this adds
more details.

# Output Files

If the data files are huge, it's necessary to conflate with a subset
of all the data. For projects using the [Tasking
Manager](https://tasks.hotosm.org/) or the Field
[Mapping Tasking Manager](https://hotosm.github.io/fmtm/) you can
download the project boundary file and use that. For other projects
you can extract administrative bondaries from OpenStreetMap, or use
external sources. Usually county administrative boundaries are a good
size. These can be extracted from OSM itself, or an external data file
of boundaries.

After conflation, an output file is created with the new buildings
that are not duplicates of existing OSM data. This is much smaller
than the original data, but still too large for anyone having
bandwidth issues. This output file is in
[GeoJson](https://geojson.org/) format, so can be edited with
[JOSM](https://josm.openstreetmap.de) or
[QGIS](https://www.qgis.org/en/site/)

Since this software is under development, rather than automatically
deleting features, it adds tags to the features. Then when editing the
data, it's possible to see the flagged data and validate the
conflation. It also makes it possible to delete manually the results
of the conflation from the output file once satisfied about the
validation of the results.

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
new building. This is done using satellite imagery. Most commercial
satellite imagery available for public use comes from Maxar. But the
different providers (Bing, ESRI, Google, etc...) have different update
cycles, so I often double check with ESRI imagery.

If there is drone imagery available from [Open Aerial
Map](https://openaerialmap.org/), that's also a good surce of imagery,
but often doesn't cover a large area.
