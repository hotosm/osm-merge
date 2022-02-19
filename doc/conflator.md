# Conflator.py

## Examples
./conflator.py -t /play/MapData/Countries/Africa/Kenya/8345-project.geojson

    Examples:
    The command: ./conflator.py -t tmsnap -p 8345 -b pg:kenya_foot -o pg:Kenya
    Reads from 3 data sources. The first one is a snapshot of the Tasking Manager database,
    and we want to use project 8345 as the boundary. Since the data files are huge, it's
    more efficient to work on subsets of all the data.

    The other two are prefixed with "pg", which defines them as a database URL instead of a file

