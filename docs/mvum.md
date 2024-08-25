# MVUM Conversion

The MVUM dataset is all of the motor vehicle roads in a national
forest. These are primarily remote dirt roads, often just a jeep
track. These are heavily used for back country access for wildland
fires and rescues. Currently much of this data has been imported in
the past, complete with all the bugs in the dataset.

This utility program normalizes the data, correcting or flagging bugs
as an aid for better conflation.

The original dataset can be found here on the USDA 
[FSGeodata
Clearinghouse](https://data.fs.usda.gov/geodata/edw/datasets.php?dsetCategory=transportation) website.

## Dataset Bugs

### Bad Reference Numbers

In some areas the MVUM data has had an 5 or a 7 prefixed to the actual
reference number. These are all usually in the same area, so I assume
whomever was doing data entry had a sticky keyboard, it got messed up
when converting from paper maps to digital, who really knows. But it
makes that tag worthless.

Another common problem in the reference nummbers is in some areas the
major maintained roads have a *.1* appended. All minor part of the
number should always have a letter appended. So *FR 432.1" is actually
*FR 432", whereas "432.1A* is correct. This was confirmed by reviewing
multiple other map sources, as the paper and PDF version of the
dataset has the correct version without the .1 appended. Obviously
this dataset is not used to produce the maps you can get from the
Forest Service.

### Missing Geometry

There are features with no geometry at all, but the tags all match an
existing feature that does have a geometry. These appear to be
accidental duplicates, so they get removed.

### Dropped Fields

These fields are dropped as they aren't useful for OpenStreetMap.

* TE_CN
* BMP
* EMP
* SYMBOL_CODE
* SEG_LENGTH
* JURISDICTION
* SYSTEM
* ROUTE_STATUS
* OBJECTIVE_MAINT_LEVEL
* FUNCTIONAL_CLASS
* LANES
* COUNTY
* CONGRESSIONAL_DISTRICT
* ADMIN_ORG
* SERVICE_LIFE
* LEVEL_OF_SERVICE
* PFSR_CLASSIFICATION
* MANAGING_ORG
* LOC_ERROR
* GIS_MILES
* SECURITY_ID
* OPENFORUSETO
* IVM_SYMBOL
* GLOBALID
* SHAPE_Length

### Preserved Fields

The field names are a bit truncated in the dataset, but these are the 

* ID is id
* NAME is name
* OPER_MAINT_LEVEL is smoothness
* SYMBOL_NAME smoothness
* SURFACE_TYPE is surface
* SEASONAL is seasonal
* PRIMARY_MAINTAINER is operator

## Abbreviations

There are multiple and somewhat inconsistent abbreviations in the MVUM
dataset highway names. OpenStreetMap should be using the full
value. These were all found by the conflation software when trying to
match names between two features. Since much of the MVUM data is of
varying quality, there's probably a few not captured here that will
have to be fixed when editing the data. This however improves good
conflation results to limit manual editing.

* " Cr " is " Creek "
* " Cr. " is " Creek "
* " Crk " is " Creek "
* " Cg " is " Campground "
* " Rd. " is " Road"
* " Mt " is " Mountain"
* " Mtn " is " Mountain"


# Tag values

## OPER_MAINT_LEVEL

This field is used to determine the smoothness of
the highway. This is not used to edit the existing smoothness value,
but it's included to help with route planning for ground-truthing.

* 5 -HIGH DEGREE OF USER COMFORT: 
Assigned to roads that provide a high degree of user comfort and
convenience. This becomes **smoothness=excellent**.

* 4 -MODERATE DEGREE OF USER COMFORT: 
Assigned to roads that provide a moderate degree of user comfort and
convenience at moderate travel speeds. This becomes
**smoothness=bad**.

* 3 -SUITABLE FOR PASSENGER CARS: 
Assigned to roads open for and maintained for travel by a prudent
driver in a standard passenger car. This becomes **smnoothness=good**.

* 2 -HIGH CLEARANCE VEHICLES: 
Assigned to roads open for use by high clearance vehicles.
This adds **4wd_only=yes** and becomes **smoothness=vary_bad**.

* 1 -BASIC CUSTODIAL CARE (CLOSED): 
Assigned to roads that have been placed in storage (&gt; one year)
between intermittent uses. Basic custodial maintenance is
performed. Road is closed to vehicular traffic. This becomes
**access=no**

## SYMBOL_NAME

Sometimes *OPER_MAINT_LEVEL* doesn't have a value, so this is used as
a backup. These values are not used to update the existing values in
OSM, they are only used for route planning ground-truthing trips.

* Gravel Road, Suitable for Passenger Car becomes *surface=gravel*
* Dirt Road, Suitable for Passenger Car becomes *surface=dirt*
* Road, Not Maintained for Passenger Car becomes *smoothness=very_bad*
* Paved Road becomes *surface=paved*

## SURFACE_TYPE

This is another field that is converted, but not used when editing the
existing OSM feature. This can only really be determined by
ground-truthing, but it converted as another aid for route planning.

* AGG -CRUSHED AGGREGATE OR GRAVEL becomes *surface=gravel*
* AC -ASPHALT becomes *surface=asphalt*
* IMP -IMPROVED NATIVE MATERIAL becomes *surface=compacted*
* CSOIL -COMPACTED SOIL becomes *surface=compacted*
* NAT -NATIVE MATERIAL becomes *surface=dirt*
* P - PAVED becomes *surface=paved*

## Options

	-h, --help            show this help message and exit
	-v, --verbose         verbose output
	-i INFILE, --infile INFILE MVUM data file
	-c, --convert         Convert MVUM feature to OSM feature
	-o OUTFILE, --outfile OUTFILE Output GeoJson file

