# TM Splitter Utility

This is a simple utility that splits a MultiPolygon into indivigual
Polygons that can be used for making data extracts using ogr2ogr or
osmium.

# Options

Usage: tm-splitter [-h] [-v] [-s] -i INFILE [-o OUTFILE]

options:
  -h, --help                             show this help message and exit
  -v, --verbose                          verbose output
  -s, --split                            Split Multipolygon
  -i INFILE, --infile INFILE             The input dataset
  -o OUTFILE, --outfile OUTFILE          Output filename
