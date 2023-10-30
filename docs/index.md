# Conflator

This is a project for conflating map data, with the ultimate goal of
importing it into [OpenStreetMap](https://www.openstreetmap.org). It
is oriented towards processing non OSM external datasets.

## Programs

### conflateBuildings.py

This looks for duplicate buildings both in the external dataset, and
in OSM. This has been used with multiple datasets, namely the
Microsoft ML Building footprints, Overture, and others.

### conflatePOI.py

This looks to find a building when the data is only a POI. Many
external datasets are a list of buildings, like schools or
hospitals. In OSM the only metadata for the feature may be
*building=yes*. Also field collected data with ODK Collect is also a
POI, and we want the data that was collected to be merged with any
existing OSM features.
