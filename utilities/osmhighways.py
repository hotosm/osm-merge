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
from progress.bar import Counter, Spinner

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
    ref = "[0-9]+[.a-z]"
    if not name:
        return name

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
            return result[0].strip()
    else:
        return result[0]
    
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
        ref = "[0-9]+[.a-z]"
        if key not in fix:
            # The OSM community has long ago decided these tags from the TIGER
            # import are useless, and should be deleted.
            if tag[0][:7] != "tiger:":
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
            ref = getRef(name)
            if ref and len(ref) > 0:
                # log.debug(f"MATCHED: {pat.pattern}")
                newtags["ref:usfs"] = f"FR {ref}"
            matched = True
            continue

        if key == "name" and name is not None:
            pat = re.compile(f"fire road")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"county road")
            if pat.match(name.lower()) and not matched:
                ref = getRef(name)
                if ref and len(ref) > 0:
                    # log.debug(f"MATCHED: {pat.pattern}")
                    newtags["ref"] = f"CR {ref.title()}"
                matched = True

            pat = re.compile(f"fs.* road")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"usfsr ")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"fs[hr] ")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                tmp = name.split(' ')
                newtags["ref:usfs"] = f"FR {tmp[1].title()}"
                matched = True

            # pat = re.compile(f"fsr road")
            # if pat.match(name.lower()) and not matched:
            #     # # log.debug(f"MATCHED: {pat.pattern}")
            #     tmp = name.split(' ')
            #     newtags["ref:usfs"] = f"FR {tmp[2].title()}"
            #     matched = True

            pat = re.compile(f"usf.* road")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"national forest road")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f".*forest service road")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                pat = re.compile(ref)
                if pat.match(name.lower()):
                    pass
                #     space  = name.rfind(' ')
                # sub  = name.rfind(' ', 0, space)
                # if len(name) - space <= 3:
                #     ref = name[sub:].replace(' ', '')
                tmp = ref.split(' ')
                newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"fr ")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"fs ")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] =  f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"forest road ")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] =  f"FR {ref.title()}"
                matched = True

            pat = re.compile(f"usfs trail ")
            if pat.match(name.lower()) and not matched:
                # log.debug(f"MATCHED: {pat.pattern}")
                ref = getRef(name)
                if ref and len(ref) > 0:
                    newtags["ref:usfs"] = f"FR {ref.title()}"
                matched = True

            if matched:
                newtags["matched"] = name
        # log.debug(f"OLDTAGS: {obj.tags}")
        # log.debug(f"NEWTAGS: {newtags}")
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
