# Conflating Building Footprints

## The data files

The Microsoft supplied data files [are at this
link](https://github.com/microsoft/KenyaNigeriaBuildingFootprints) for
Kenya and Nigeria. Files for Uganda and Tanzania [are at this
link](https://github.com/microsoft/Uganda-Tanzania-Building-Footprints).
These contain ML/AI derived building footprints from
[Maxar](https://www.maxar.com/) satellite imagery. 

For raw OSM data, the existing country data is downloaded from [GeoFabrik](
https://download.geofabrik.de/index.html), and imported using a
modified schema for osm2pgsql.

> osm2pgsql --create -d nigeria --extra-attributes --output=flex --style raw.lua nigeria-latest-internal.osm.pbf

The *raw.lua* script is [available
here](https://github.com/hotosm/underpass/blob/master/raw/raw.lua). It's
part of the [Underpass
project](https://hotosm.github.io/underpass/index.html). It uses a
more compressed and efficient data schema.

Once the data is imported, do this to improve query performance.
> cluster ways_poly using ways_poly_geom_idx;

> create index on ways_poly using gin(tags);

The building footprint data file is imported into Postgres using [ogr2ogr](https://gdal.org/programs/ogr2ogr.html).

> ogr2ogr -skipfailures -progress -overwrite -f PostgreSQL PG:dbname=nigeria_foot -nlt POLYGON nigeria.geojsonl -lco COLUMN_TYPES=other_tags=hstore

While any name can be used for the databases, I usually default to
naming the [OpenStreetMap](http://download.geofabrik.de/index.html)
database the country name as used in the data file, and then append
*_foot* to the country name for the building footprints. The building
footprints contain no tags, just polygons. Since only new buildings
are in the final data file from conflation, two tags are added,
**source=bing** and **building=yes**.

## Checks Made

### Conflation

The primary check is identifying duplicate buildings and overlapping
buildings. This is done by loading both data files, the building
footprints and OpenStreetMap into Postgres. Most of the actual work us done using
[Postgres](https://www.postgresql.org/) [OGR](https://gdal.org/api/python.html).

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
building. Instead the entire block of buildings is a single
polygon. While it would be possible to automatically correct this,
that task is not supported by this tool.

The other problem is that as processing satellite imagery is that
buildings are recognized by shading differences, so often features are
flagged as buildings that don't actually exist. For example, big rocks
in the desert, or high mountain snowfields both get marked as a
building. Any building in the footprints data that has no other
buildings nerby, nor a highway or path of some kind is flagged with a
debugging tag of *false=yes*. Usually this is easy to determine
looking at satellite imagery, since there are often remote
buildings. The tags can be searched for ehen editing the data to
visually determine whether it's a real building or not.

# Input Files

While the [conflator.py](conflator.md) program works equally as well
using a database or disk files, disk files are more convienient for
validating the conflation results. Once all the Tasking Manager
project boundaries are downloaded using the [splitter.py](splitter.md)
program, these utilities are oriented towards batch processing an entire
directory of data files, which needs to be done after updating any of
the raw data sources. This processing is handled by a few
[utilities](utilities.md), which produce two files used for input to
the conflator program. The are *123435*-osm.geojson*, and
*12345-ms.geojson". One just contains the OSM buildings, and the other
the building footprint file.

# Output Files

As the country wide input data files are huge, it's necessary to
conflate buildings with a subset of all the data. Commonly county
administrative boundaries are a good size. These can be extract from
OSM itself, or an external data file of boundaries. The initial set of
output files is the building data chopped up into smaller
files. Project boundaries can also be downloaded from the HOT [Tasking
Manager](https://www.tasks.hotosm.org) which is common for building
imports.

After conflation, an output file is created with the new buildings
that are not duplicates of existing OSM data. This is much smaller
than the original data, but still too large for anyone having
bandwidth issues. The utility program[splitter.py](splitter.md) takes
a file or database that contains boundaries and produces multiple data
files, one for each boundary. This output file is in
[GeoJson](https://geojson.org/) format, so can be edited with
[JOSM](https://josm.openstreetmap.de) or
[QGIS](https://www.qgis.org/en/site/)

The final output files are for the Tasking Manager. This uses a file
of the task boundaries within a project boundary. These can be
extracted from the Tasking Manager's REST API like so:

> https://tasks.hotosm.org/api/v2/projects/12315/tasks/?as_file=false

The files are in GeoJson format. The splitter.py program uses the X and Y
indexes of each task to give each output file a unique name. In the
instructions for a Tasking Manager project, it's possible to embed the
URL of a remote file that gets loaded into JOSM automatically when
that task is selected to map. As this file is after conflation, it is
relatively small.

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
