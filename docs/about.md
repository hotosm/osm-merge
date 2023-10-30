# Conflator

This is a project for conflating map data, with the ultimate goal of
importing it into [OpenStreetMap](https://www.openstreetmap.org)(OSM).

It is oriented towards conflating external datasets with existing OSM
data. External data is usually polygons (building footprints), or
POIs. These days there are multiple publically available building
footprint datasets with an appropriate license for OSM. The problem is
this data needs to be validated.

Due to the flexibility of the OSM data schema, it's impossible to get
100% perfect conflation. But the purely manual conflation is very
time consuming and tedious. This project aims to do as much as
possible to aid the validator to make their work as efficient as
possible.
