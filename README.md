# OSM Merge

<!-- markdownlint-disable -->
<p align="center">
  <em>Merge features and tags into existing OSM data.</em>
</p>
<p align="center">
  <a href="https://github.com/hotosm/osm-merge/actions/workflows/build.yml" target="_blank">
      <img src="https://github.com/hotosm/osm-merge/actions/workflows/build.yml/badge.svg" alt="Build">
  </a>
  <a href="https://github.com/hotosm/osm-merge/actions/workflows/build-ci.yml" target="_blank">
      <img src="https://github.com/hotosm/osm-merge/actions/workflows/build-ci.yml/badge.svg" alt="CI Build">
  </a>
  <a href="https://github.com/hotosm/osm-merge/actions/workflows/docs.yml" target="_blank">
      <img src="https://github.com/hotosm/osm-merge/actions/workflows/docs.yml/badge.svg" alt="Publish Docs">
  </a>
  <a href="https://github.com/hotosm/osm-merge/actions/workflows/publish.yml" target="_blank">
      <img src="https://github.com/hotosm/osm-merge/actions/workflows/publish.yml/badge.svg" alt="Publish">
  </a>
  <a href="https://github.com/hotosm/osm-merge/actions/workflows/pytest.yml" target="_blank">
      <img src="https://github.com/hotosm/osm-merge/actions/workflows/pytest.yml/badge.svg" alt="Test">
  </a>
  <a href="https://pypi.org/project/osm_merge" target="_blank">
      <img src="https://img.shields.io/pypi/v/osm_merge?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://pypistats.org/packages/osm_merge" target="_blank">
      <img src="https://img.shields.io/pypi/dm/osm_merge.svg" alt="Downloads">
  </a>
  <a href="https://github.com/hotosm/osm-merge/blob/main/LICENSE.md" target="_blank">
      <img src="https://img.shields.io/github/license/hotosm/osm-merge.svg" alt="License">
  </a>
</p>

---

📖 **Documentation**: <a href="https://hotosm.github.io/osm-merge/" target="_blank">https://hotosm.github.io/osm-merge/</a>

🖥️ **Source Code**: <a href="https://github.com/hotosm/osm-merge" target="_blank">https://github.com/hotosm/osm-merge</a>

---

<!-- markdownlint-enable -->

## Background

This is a project for conflating external map datasets with
OpenStreetMap with the ultimate goal of importing it into
[OpenStreetMap](https://www.openstreetmap.org). It
is oriented towards processing non OSM external datasets and supports
field data collection using
[OpenDataKit](https://opendatakit.org/software/), Motor Vehicle Use
Maps
[(MVUM)](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.Road_MVUM.zip)
from the US National Forest Service,
and [Trail
maps](https://data.fs.usda.gov/geodata/edw/edw_resources/shp/S_USA.TrailNFS_Publish.zip)
from the National Park Service.

The goal of this project is two-fold. One is to support field data
collection using OpenDataKit. The
[osm-fieldwork](https://hotosm.github.io/osm-fieldwork/) project can
be used to convert the ODK data files into
[GeoJson](https://geojson.org/) and [OSM
XML](https://wiki.openstreetmap.org/wiki/OSM_XML). This
project then supports conflating that field collected data with
current OpenStreetMap. Otherwise this is a time-consuming process to
do manually.

![Women field mapping](assets/small-zanzibar.jpg){width=300 height=200}

The other goal is focused on emergency and recreational access in
remote areas. This is using the Motor Vehicle Use Map (MVUM) datasets
of all highways (mostly jeep trails) and the park service trails to
improve the existing features in OpenStreetMap.  The current data in
OpenStreetMap was often imported complete with bugs in the original
dataset, or the only details are *highway=track*. All of these have a
US forest service reference number and name. Adding those makes it
much easier to communicate a location.

![Way up Rollins Pass](assets/small-rollinspass.png){width=300 height=200}


This project uses a huge amount of data (and disk space) if you start
from the original nation wide datasets, which are too large to
edit. There is a contrib script in the git sources I use to start
breaking down the huge files into managable pieces.

## Programs

This project comprises of a main program, and multiple utilities. The
utilities are used to prepare the datasets for conflating by fixing
known bugs.

### conflator.py

This program doesn't require a database, unlike the other conflation
programs in this project, although adding database support is on the
TODO list. It is focused on [conflating OpenDataKit](odkconflation.md)
with OpenStreetMap, as well as conflating [rural
highways](highways.md). It'll conflate any two datasets in either
GeoJson or OSM XML format. While this is currently under heavy
development and debugging. I've been processing large amounts of data
to track down all the obscure bugs in the original datasets, or the
conflation process.

![MVUM Signs](assets/20210913_113539.jpg){width=300 height=200}

### The Data

Much of the process of conflation is splitting huge datasets into
managable sized files. Since that process is [mostly
automated](https://github.com/hotosm/osm-merge/tree/main/contrib), I
have a collection of files where I have done that part. Since
conflation also requires converting the original datasets, the
original files are included, the converted files to OSM XML & GeoJson,
and the results of conflation. Not all the national forests and parks
have been conflated yet, but the data is there for others that may
wish to try. The processed map data is available [from
here](http://5.78.72.214/fieldmapper/).

![Skipped highway segments](assets/skippedsegments.png){width=300 height=200}

