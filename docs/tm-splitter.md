This program manages tasks splitting

options:
  -h, --help            show this help message and exit
  -v, --verbose         verbose output
  -i INFILE, --infile INFILE
                        The input dataset
  -g, --grid            Generate the task grid
  -s, --split           Split Multipolygon
  -o OUTFILE, --outfile OUTFILE
                        Output filename
  -e EXTRACT, --extract EXTRACT
                        Split Dataset with Multipolygon
  -t THRESHOLD, --threshold THRESHOLD
                        Threshold

This program implements some HOT Tasking Manager style functions
for use in other programs. This can generate a grid of tasks from an
AOI, and it can also split the multipolygon of that grid into seperate
files to use for clipping with ogr2ogr.

For Example, this will create a multipolygon file of the grid. ).1 is
about the right size for TM task within the project.

	tm-splitter.py --grid --infile aoi.geojson --threshold 0.1

To break up a large public land boundary, a threshold of 0.7 gives
us a grid of just under 5000 sq km, which is the TM limit.

	tm-splitter.py --grid --infile boundary.geojson --threshold 0.7

To split the file into tasks, split it:

	tm-splitter.py --split --infile tasks.geojson
