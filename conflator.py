#!/usr/bin/python3
#
# Copyright (c) 2020, 2021 Humanitarian OpenStreetMap Team
#
# This file is part of Underpass.
#
#     Underpass is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     Underpass is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with Underpass.  If not, see <https://www.gnu.org/licenses/>.

import logging
import getopt
from sys import argv


options = dict()
options["schema"] = "ogr2ogr";
options["database"] = None;
options["infile"] = None;

def usage():
    out = """
    --help(-h)       Get command line options
    --verbose(-v)    Enable verbose output
    --database(-d)   Database URL (host= user= password=)"
    --infile(-i)     Input data file
    --schema(-s)     Database schema (pgsnapshot, ogr2ogr, osm2pgsql) defaults to \"%s\"
    """ % (options['schema'])
    print(out)
    quit()

if len(argv) <= 1:
    usage()

try:
    (opts, val) = getopt.getopt(argv[1:], "h,v,d:,i:,s:",
        ["help", "verbose", "database", "infile", "schema"])
except getopt.GetoptError as e:
    logging.error('%r' % e)
    usage(argv)
    quit()

for (opt, val) in opts:
    if opt == '--help' or opt == '-h':
        usage()
    elif opt == "--database" or opt == '-d':
        options['database'] = val
    elif opt == "--schema" or opt == '-s':
        options['schema'] = val
    elif opt == "--infile" or opt == '-i':
        options['infile'] = val

if options['infile'] is None and options['database'] is None:
    usage()

