# Utilities

Conflator includes a few bourne shell scripts used for bulk
processing of data files. Because of the poor performance when
processing huge data files, they're split up into manageable
pieces. There are several assumptions made, namely that the OSM data
is in postgres database, imported via [these
instructions](conflation.md). The building footprint file can be
either in a database, or the downloaded GeoJson formatted data file.

Since all of the output files need to be web accessible, these scripts
are usually run in the directory containing the data files. Each
country should be in a separate directory. These scripts take two
command line arguments, the country to be processed, and optionally a
single project to process. By default all projects are processed. If a
consistent naming convention is used, the basename of the current
directory is to try to guess the proper country name. That same value
is also used to identify the correct database or data file name.

### For example

	~www/Africa/Kenya
	~www/Africa/Kenya/kenya-latest.pbf
	~www/Africa/Kenya/kenya.geojsonl
	~www/Africa/Nigeria
	~www/Africa/Nigeria/nigeria-latest.pbf
	~www/Africa/Nigeria/nigeria.geojsonl
	~www/Asia/Nepal
	~www/Asia/Nepal/...

# Tasking Manager Projects

Since the import data is huge, the Tasking Manager is used to
validation the results of conflation. To further reduce the data size,
the project boundaries are downlooaded from the Tasking Manager by
using it's remote API. These are then saved to disk using the naming
convention *12345-project.geojson*, where **12345** is a project
ID. The project boundaries can downloaded using the
[splitter.py](splitter.md) program, which is part of conflator. A
boundary can be downloaded like this:

> PATH/splitter.py -p 12345

Since a big import requires multiple Tasking Manager projects, to get
started, download all of the boundaries for this import.

## clipsrc.sh

This script extracts all the buildings in the specified country into a
data file. This assumes all the data has already been imported into
postgres. Since there are usually multiple countries imported into
postgres, this gets just the ones we want for furthur processing. 

This generates two output files from the database, namely the country
name, postfixed by the data source. For example *kenya-osm.geojson*
and *kenya-ms.geojson*. These data files are then split into
smaller files based on a Tasking Manager project boundary. Each of the
smaller files follows the same naming convention, *12345-osm.geojson*
or *kenya-ms.geojson*.

> PATH/clipsrc.sh kenya

## update.sh

This script processes the project sized data files for the best
performance. One again, it looks for any files that follow the naming
convention, and runs the [conflation script](conflator.md) on each of
the project boundaries. The generates a single output file, containing
buildings from the footprint file that are not already in OSM. This
file is *12345-buildings.geojson*.

> PATH/clipsrc.sh nigeria

## index.sh

This script generates a simple webpage to navigate all the data files,
so they can be manually downloaded for validation. This script should
be run in the directory with all the data files. The first section is
just the project from the Tasking Manager, the rest are all the
smaller files for each project. Each project has 3 generated data
files, the two raw data files produced from the database, and the
conflated building output.

> ./index.sh
