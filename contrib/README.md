This script is used to create and maintain a large collection of
dataset from multiple sources. It is currently focused on National
Forests and National Parks in Utah, Colorado, and Wyoming. It'd be
easy to add other states or categories like National Monuments.

It is designed to be simple to modify. Most of this is just
running ogr2ogr and osmium in a loop splitting big files into
progressively smaller ones. Everything is driven by the boundary
multipolygons. Splitting up all the files and making extracts can take
a considerable amount of time, but once done, you can start mapping.

There is obviously a proper order. First start by splitting the
multipolygon boundary of the national forest or park. That generates
the a new multipolygon of the tasks. Each task is the maximum size for
a Tasking Manager project, which is 5000sq km. That file is then split
into indivigual files, one for each TM project. Ogr2ogr and osmium are
used to make data extracts for each project AOI.

The HOT Tasking Manager will split this project into smaller
tasks. When mapping, load the conflated dataset, and the external
datasets as layers in JOSM.

To make editing easier, the TM project boundary is split into
tasks. TM lets you upload a custom task file, so we create our
own. Then the data extracts are split again, one for each task. These
small files are much easier to work with.
