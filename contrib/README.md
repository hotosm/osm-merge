This script is used to create and maintain a large collection of
dataset from multiple sources. It is currently focused on National
Forests and National Parks in Utah, Colorado, and Wyoming. It'd be
easy to add other states or categories like National Monuments.

It is designed to be simple to modify. Most of this is just
running ogr2ogr and osmium in a loop splitting big files into
progressively smaller ones. Everything is driven by the boundary
multipolygons.


