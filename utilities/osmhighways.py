#!/usr/bin/python3

# Copyright (c) 2021, 2022, 2023, 2024 Humanitarian OpenStreetMap Team
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
    
import argparse
import logging
import sys
import os
from sys import argv
from codetiming import Timer
from pathlib import Path
import osmium
import re
from progress.spinner import Spinner

# https://prd-tnm.s3.amazonaws.com/index.html?prefix=StagedProducts/TopoMapVector/

# Instantiate logger
log = logging.getLogger(__name__)

def getRef(name) -> str:
    """
    Extract the reference number in the name string

    Args:
        name (str): The name of the highway

    Returns:
        (str): The reference number, which is an alphanumeric
    """
    if not name:
        # log.error(f"Nothing done, empty string")
        return name

    # The number is always (supposedly) last, so this gets all the
    # weird contortions without getting complicated.
    ref = "[0-9].*+"
    pat = re.compile(ref)
    result = pat.findall(name.lower())
    if len(result) == 0:
        # if it's as a an integer, not decimals or character appended,
        # look for that too.
        ref = " [0-9]+"
        pat = re.compile(ref)
        result = pat.findall(name.lower())
        if len(result) == 0:
            return name
        else:
            return result[0].strip().replace(' ', '.')
    else:
        if '/' in result[0]:
            return result[0]
        else:
            return result[0].replace(' ', '.')
    
def filterTags(obj):
    """
    Filter the tags, which entails fixing typos, abbreviations, etc...

    Args:
        obj: The feature to filter

    Returns:
    
    """
    fix = ["name", "ref", "ref:usfs"]

    name = None
    newtags = dict() # obj.tags
    if "name" in obj.tags:
        name = obj.tags.get("name")
    # log.debug(f"NAME: {name}")
    for tag in obj.tags:
        matched = False
        key = tag[0]
        val = tag[1]
        # The OSM community has long ago decided these tags from the
        # TIGER import are useless, and should be deleted.
        if key[:6] == "tiger:":
            continue
        if key not in fix:
            newtags[key] = val
            continue

        # It's the name tag that has the most problems.
        if key == "ref" or key == "ref:usfs":
            # A good ref has an FR or FS prefixed, so just use it, but move it
            # to the ref:usfs tag.
            if val[:3] == "FS " or val[:3] == "FR ":
                newtags["ref:usfs"] = val
                continue
            elif val[:4] == "FSR ":
                ref = getRef(val)
                newtags["ref:usfs"] = f"FR {ref}"
                continue
            elif key == "ref" and val[:3] == "CR ":
                # It's a well mapped county road, do nothing
                newtags[key] = val
                continue
            ref = getRef(name)
            if ref and len(ref) > 0:
                # log.debug(f"MATCHED: {pat.pattern}")
                newtags["ref:usfs"] = f"FR {ref}"
            matched = True
            continue

        usfspats = ["fire road",
                    "fs.* road",
                    "f[sd]r ",
                    "usfsr ",
                    "fs[hr] ",
                    "usf.* road",
                    "national forest road",
                    "forest service road",
                    "fr ",
                    "fs ",
                    "forest road",
                    "usfs trail ",
                    ]
        if key == "name" and name is not None:
            pat = re.compile("county road")
            if pat.match(name.lower()):
                for entry in name.split(';'):
                    ref = getRef(entry)
                    # log.debug(f"COUNTY: {pat.pattern} REF={ref.title()} NAME={name}")
                    if ref and len(ref) > 0:
                        newtags["ref"] = f"CR {ref.title()}"
                    matched = True
                continue

            # FIXME: Since we're focused on roads in national forests or
            # parks, there shouldn't be any state or federal highways,
            # but you never know, this should be confirmed.
            # pat = re.compile("state highway")
            # pat = re.compile("united states highway")

            for regex in usfspats:
                pat = re.compile(regex)
                if pat.match(name.lower()):
                    for entry in name.split(';'):
                        ref = getRef(entry)
                        # log.debug(f"MATCHED: {pat.pattern} REF={ref.title()} NAME={name}")
                        if ref and len(ref) > 0:
                            newtags["ref:usfs"] = f"FR {ref.title()}"
                    matched = True
                    break
            if not matched:
                newtags[key] = val
        else:
            newtags[key] = val

    # print(f"OLDTAGS: {len(obj.tags)}: {obj.tags}")
    # print(f"NEWTAGS: {len(newtags)} {newtags}")
    return newtags
    
def main():
    """This main function lets this class be run standalone by a bash script"""
    parser = argparse.ArgumentParser(
        prog="usgs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="This program extracts highways from OSM",
        epilog="""

    For Example: 
        osm.py -v -i WY_Roads.osm
        """,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("-i", "--infile", required=True, help="Top-level input directory")
    parser.add_argument("-o", "--outfile", default="out.osm", help="Output file")

    args = parser.parse_args()

    # if verbose, dump to the terminal.
    if args.verbose:
        log.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(threadName)10s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        log.addHandler(ch)

    # FIXME: this should change
    outfile = args.outfile
    keep = ["track",
            "unclassified",
            "residential",
            "path",
            "footway",
            "pedestrian"
            "primary",
            "secondary",
            "tertiary",
            "trunk",
            "motorway",
            ]
    spin = Spinner('Processing...')
    fp = osmium.FileProcessor(args.infile).with_filter(osmium.filter.KeyFilter('highway'))
    with osmium.BackReferenceWriter(outfile, ref_src=args.infile, overwrite=True) as writer:
        for obj in fp:
            spin.next()
            if obj.tags['highway'] in keep and obj.is_way():
                tags = filterTags(obj)
                # obj.tags = new
                # if new != obj.tags:
                #     log.debug(f"Tags changed! {new}")
                writer.add(obj.replace(tags=tags))
                # writer.add(obj)
    log.info(f"Wrote {outfile}")

if __name__ == "__main__":
    """This is just a hook so this file can be run standlone during development."""
    main()
