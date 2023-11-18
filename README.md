# Conflator

<!-- markdownlint-disable -->
<p align="center">
  <img src="https://github.com/hotosm/fmtm/blob/main/images/hot_logo.png?raw=true" style="width: 200px;" alt="HOT"></a>
</p>
<p align="center">
  <em>Conflate OSM data.</em>
</p>
<p align="center">
  <a href="https://github.com/hotosm/conflator/actions/workflows/build.yml" target="_blank">
      <img src="https://github.com/hotosm/conflator/actions/workflows/build.yml/badge.svg" alt="Build">
  </a>
  <a href="https://github.com/hotosm/conflator/actions/workflows/build-ci.yml" target="_blank">
      <img src="https://github.com/hotosm/conflator/actions/workflows/build-ci.yml/badge.svg" alt="CI Build">
  </a>
  <a href="https://github.com/hotosm/conflator/actions/workflows/docs.yml" target="_blank">
      <img src="https://github.com/hotosm/conflator/actions/workflows/docs.yml/badge.svg" alt="Publish Docs">
  </a>
  <a href="https://github.com/hotosm/conflator/actions/workflows/publish.yml" target="_blank">
      <img src="https://github.com/hotosm/conflator/actions/workflows/publish.yml/badge.svg" alt="Publish">
  </a>
  <a href="https://github.com/hotosm/conflator/actions/workflows/pytest.yml" target="_blank">
      <img src="https://github.com/hotosm/conflator/actions/workflows/pytest.yml/badge.svg" alt="Test">
  </a>
  <a href="https://pypi.org/project/conflator" target="_blank">
      <img src="https://img.shields.io/pypi/v/conflator?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>
  <a href="https://pypistats.org/packages/conflator" target="_blank">
      <img src="https://img.shields.io/pypi/dm/conflator.svg" alt="Downloads">
  </a>
  <a href="https://github.com/hotosm/conflator/blob/main/LICENSE.md" target="_blank">
      <img src="https://img.shields.io/github/license/hotosm/conflator.svg" alt="License">
  </a>
</p>

---

📖 **Documentation**: <a href="https://hotosm.github.io/conflator/" target="_blank">https://hotosm.github.io/conflator/</a>

🖥️ **Source Code**: <a href="https://github.com/hotosm/conflator" target="_blank">https://github.com/hotosm/conflator</a>

---

<!-- markdownlint-enable -->

## Background

This is a project for conflating map data,
with the ultimate goal of importing it into
[OpenStreetMap](https://www.openstreetmap.org). It
is oriented towards processing non OSM external datasets.

## Programs

### conflateBuildings.py

This looks for duplicate buildings both in the
external dataset, and in OSM. This has been used with
multiple datasets, namely the Microsoft ML Building
footprints, Overture, and others.

### conflatePOI.py

This looks to find a building when the data is only a POI. Many
external datasets are a list of buildings, like schools or
hospitals. In OSM the only metadata for the feature may be
_building=yes_. Also field collected data with ODK Collect is also a
POI, and we want the data that was collected to be merged with any
existing OSM features.
