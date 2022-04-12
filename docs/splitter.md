# Splitter Program

Splitter is a utility to chop up large files into smaller, more
manageable sizes. While it would be possible to do this with other
utlities like ogr2ogr, this has Tasking M<anager integration. While it
is possible to download the project boundary from the Tasking Manager,
this also supports querying the Tasking Manager database
directly. This is especially useful when splitting a data file into
the same size as a mapping task in Tasking Manager. This supports
mappers without high-speed internet access. As some projects contain
many hundreds of tasks, this would be time consuming to do manually.

This uses GDAL to do the actual work. Rather than use any of the
higher-level python modules, the needs here dodn't need the extra
layers of code.

# Usage

    --help(-h)       Get command line options
    --verbose(-v)    Enable verbose output
    --infile(-i)     Input data file in any OGR supported format OR
    --tmdatabase(-t) Tasking Manager database to split
    --splittasks(-s) When using the Tasking Manager database, split into tasks
    --buildings(-b)  Building footprint database to split
    --project(-p)    Tasking Manager project ID to get boundaries
    --outdir(-o)     Output directory for output files (default "/tmp")
    --boundary(-b)   Specify a multipolygon as a boundaries, one file for each polygon

There are two input datasets. One is the boundary of the Tasking
Manager project, and the other is the raw data to be split. Any file
format supported by GDAL can be used. The output is a GeoJson file or
files. The boundary can also be obtained from the Tasking Manager
database directly.

## Examples

Uses 2 disk files, *8345-project.geojson* is a boundary downloaded from
the Tasking Manager, or manually extracted from the database. There is
a simple utility script **extract.sh** which takes a project ID, and
uses it to produce two output files. One is the project boundary
polygon, and the other is a series of polygons, one for each task
square within the project boundary. WHen the fils of task boundaries
is used, it will generate a separate file for each task. Sometimes
this may create hundreds of small files. The project ID and Task ID is
part of the file name.

The command:
 splitter.py -b 8345-project.geojson -i kenya.geojsonl

 creates *tmproject-8345.geojson*

The command:
 splitter.py -b 8345-tasks.geojson -i kenya.geojsonl

 creates *tmproject-8345-task-[0-9]+.geojson*

The command
 splitter.py -p 8345 -t tmsnap -i kenya.geojsonl

 creates *tmproject-8345.geojson*, by getting the boundary from a database

The command:
 splitter.py -p 8345 -t tmsnap -s -i kenya.geojsonl

 creates *tmproject-8345-task-[0-9]+.geojson*, by getting the task boundaries from a database

















