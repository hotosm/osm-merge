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

## Highways

Highways are more complex because it uses relations. A relation is a
groups of highway segments into a single entity. Some times the tags
are on the relation, other times each highway segment. The segments
change when the highway condition changes, but the name and reference
number doesn't change. External datasets don't use relations, they are
OSM specific.

### MVUM Highways

The USDA publishes a dataset of [Motor Vehicle Use Maps
(MVUM)](https://www.fs.usda.gov/detail/psicc/maps-pubs/?cid=stelprdb5177824
) highways in the National Forest. Some of this data has already been
imported into OSM, although the metadata may be lacking, but the
LineString is there. MVUM roads are primarily compacted dirt
roads. While some can be driven in a passenger vehicle, most are
varying degrees of bad to horrible to impassable. These highways are
often used for recreational traffic by off-road vehicles, or for
emergency access for a wildland fire or backcountry rescue.

Another key detail of MVUM highways is each one may have 4 names!
There is of course the primary name, for example "Cedar Lake
Road". But it may also have a *locals* name, common in remote
areas. And then there is the reference number. A MVUM highway may have
two reference numbers, the country designated one, and the USDA
one. Luckily OSM supports this. Many of these tags effect both how
the highway is displayed, as well as routing for navigation. 

	"name": "Platte Lake Road",
	"alt_name": "Bar-K Ranch Road",
	"surface": "dirt",
	"smoothness": "bad",
	"highway": "track",
	"ref": "CO 112",
	"ref:usfs": "FR 521.1A"
	"tracktype": "grade3"

A *bad* highway is something I'd be comfortable driving in a 4x4
high-clearance vehicle. Smoothness values can be a bit misleading, as
often what is in OSM may be years out of date. And most MVUM roads get
zero maintainance, so get eroded, pot-holed, and or exposed rocks. And
people's perception of road conditions is subjective based on one's
experience driving these highways.

All of this metadata makes conflation interesting. Since existing OSM
features were added by more than one person, the tagging may not be
consistent. For example, the existing data may have *Forest Service
Road 123*, which should really be **ref:usfs=FR 123**. And the real
highway name *Piney Pass Road* is in the MVUM dataset. The goal of
highway conflation is to merge the new metadata into the existing OSM
feature where possible. This then needs to be validated by a human
being. There is still much tedious work to process post conflation
data before it can be uploaded to OSM.

But sometimes conflation works well, especially when the LineString
in OSM was imported from older versions of the MVUM data. But often
highways in OSM were traced off satellite imagery, and may have wildly
different geometry.

If you ignore conflating the tags other than name or ref, the process
is somewhat less messy. And tags like *surface* and *smoothness*
really should be ground-truthed anyway. So I do ignore those for now
and stick to validating the name and the two reference numbers which
are usually lacking in OSM. That and addding consistency to the data
to make it easier to make data extracts.

To conflate OSM highways with external data, initially each entry in
the external dataset does a distance comparison with the existing OSM
data. There is an optional threshold to set the distance limit. Since
currently this is focused on conflating files without a database, this
is computationally intensive, so slow. For data that was imported in
the past from MVUM datasets, a distance of zero means it's probably
the same segment. The external dataset needs to have the tagging
converted to the syntax OSM uses. Tagging can be adjusted using a
conversion program, but as conversion is usually a one-off task, it
can also be done using JOSM or QGIS. Usually it's deleting most of the
tags in the external dataset that aren't appropriate for
OSM. Primarily the only tags that are needed are the *name* and any
reference numbers. Since the MVUM data also classified the types of
road surface, this can also be converted. Although as mentioned, may
be drastically out of data, and OSM is more recent and ground-truthed.

Then there is a comparison of the road names. It's assumed the one from
the MVUM dataset is the correct one. And since typos and weird
abbreviations may exist in the datasets, fuzzy string matching is
performed. This way names like *FS 123.1* can match *FR 123.1A*. In
this case the current name value in OSM becomes *alt_name*, and the
MVUM name becomes the official name. This way when validating you can
make decisions where there is confusion on what is correct. For an
exact name match no other tags are checked to save a little time.

Any other processing is going to be MVUM highway specific, so there
will be an additional step to work through the reference numbers not
supported by this program.

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
