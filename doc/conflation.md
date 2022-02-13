# Conflating Building Footprints

## The data files

The Microsoft supplied data files [are at this
link](https://github.com/microsoft/KenyaNigeriaBuildingFootprints). These
contain ML/AI derived building footprints from
[Maxar](https://www.maxar.com/) satellite imagery. 

For raw OSM data, the existing country data is downloaded from [GeoFabrik](
https://download.geofabrik.de/index.html).

Both data files are imported into Postgres using [ogr2ogr](https://gdal.org/programs/ogr2ogr.html).

## Checks Made

### Conflation

The primary check is identifying duplicate buildings and overlapping
buildings. This is done by loading both data file, the footprints and
OSM into Postgres. Most of the actual work us done using
[Postgres](https://www.postgresql.org/) and
[PostGIS](https://postgis.net/). 

## Know Problems

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
building.

