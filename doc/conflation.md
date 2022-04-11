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
modified schaeme for osm2pgsql.

> osm2pgsql --create -d nigeria --extra-attributes --output=flex --style /data/raw.lua nigeria-latest-internal.osm.pbf

Once the data is imported, do this to improve performance.
> cluster ways_poly using ways_poly_geom_idx;

> create index on ways_poly using gin(tags);

The building footprint data file is imported into Postgres using [ogr2ogr](https://gdal.org/programs/ogr2ogr.html).

> ogr2ogr -skipfailures -progress -overwrite -f PostgreSQL PG:dbname=nigeria_foot -nlt POLYGON nigeria.geojsonl -lco COLUMN_TYPES=other_tags=hstore

## Checks Made

### Conflation

The primary check is identifying duplicate buildings and overlapping
buildings. This is done by loading both data file, the footprints and
OSM into Postgres. Most of the actual work us done using
[Postgres](https://www.postgresql.org/) and
[PostGIS](https://postgis.net/).

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

# Output files

As the data files are huge, it's necessary to conflate buildings with
a subset of all the data. Commonly county administrative boundaries
are a good dize. These can be extract from OSM itself, or an external
data file of boundaries. The initial set of output files are the
building data chopped up into regionaly boundaries.

After conflation, another output file is created with the new
buildings that are not duplicates of existing OSM data. This is much
smaller than the original data, but still too large for anyone having
bandwidth issues. The utility program[splitter.py](splitter.md) takes
a file or database that contains boundaries and produces multiple data
files, one for each task.

The final output files are for the Tasking Manager. This uses a file
of the task boundaries withint a project boundary. These can be
extracted from the Tasking Manager's REST API like so:

 https://tasking-manager-staging-api.hotosm.org/api/v2/projects/8612/tasks/?as_file=false

The file is in geojson format. The splitter.py program uses the X and Y
indexes of each task to give each output file a unique name. In the
instructions for a Tasking Manager project, it's possible to embed the
URL of a remote file that gets loaded into JOSM automatically when
that task is selected to map. As this file is after conflation, it is
relatively small.
