# National Park Service Trails

This processes both the National Park Service trails dataset, and the
National Forest Service trail datasets. The schema of the two datasets
is very similar. One of the differences is for Park Service Trails has
two default tags in the output file which are *bicycle=no* and
*motor_vehicle=no*. These default tags are [documented
here](https://wiki.openstreetmap.org/wiki/US_National_Park_Service_Tagging:_Trails).

This dataset is available in a variety of formats from the [ArcGIS Hub](https://hub.arcgis.com/datasets/fedmaps::national-park-service-trails/about).

## Processed Fields

These are the fields extracted from the data that are converted to
OpenStreetMap syntax so they can be conflated.

* OBJECTID becomes **id**
* TRLNAME becomes **name**
* TRLCLASS becomes **sac_scale**
* TRLUSE becomes *yes* for **horse**, **bicycle**, **atv**, etc...
* TRLALTNAME becomes **alt_name**
* SEASONAL becomes **seasonal**
* MAINTAINER becomas **operator**
* TRLSURFACE becomes **surface**

## Dropped Fields

These fields are all ignored, and are dropped from the output file.

* MAPLABEL
* TRLSTATUS
* TRLTYPE
* PUBLICDISP
* DATAACCESS
* ACCESSNOTE
* ORIGINATOR
* UNITCODE
* UNITNAME
* UNITTYPE
* GROUPCODE
* GROUPNAME
* REGIONCODE
* CREATEDATE
* EDITDATE
* LINETYPE
* MAPMETHOD
* MAPSOURCE
* SOURCEDATE
* XYACCURACY
* GEOMETRYID
* FEATUREID
* FACLOCID
* FACASSETID
* IMLOCID
* OBSERVABLE
* ISEXTANT
* OPENTOPUBL
* ALTLANGNAM
* ALTLANG
* NOTES

## National Forest Service Trails

The US Forest Service makes much of their data publically accessible,
so it's been a source for imports for a long time. There is a nice
detailed wiki page on the [Forest Service
Data](https://wiki.openstreetmap.org/wiki/US_Forest_Service_Data). The
conversion process handles most of the implementation details.

# Keep Fields

The two primary fields are *TRAIL_NO*, which is used for the
*ref:usfs* tags, and *TRAIL_NAME*, which is the name of the trail. In
addition to these

## The 5 Variations

For many of the features classes, there are 5 variations on each one
which is used for access.

* Managed: Usage allowed and managed by the forest service
* Accepted: Usage is accepted year round
* Accepted/Discouraged: Usage is accepted, but discouraged
* Restricted: Usage is restricted
* Discouraged: Usage is discouraged

These are converted to the apppropriate value.

* Managed* sets the keyword to **designated**
* Accepted* sets the keyword to **yes**
* Restricted* sets the keyword to **no**
* Discouraged* sets the keyword to **discouraged**
* Accepted/Discouraged* sets the keyword to **permissive**

Many of the values for these are NULL, so ignored when generating the
output file. If the value exists, it's either a **Y** or a **N**, which
is used to set the values. For example: "SNOWMOBILE": "Y" becomes
**snowmobile=yes** in the output file.

* PACK_SADDLE_ becomes **horse=**
* BICYCLE_ becomes **bicycle=**
* MOTORCYCLE_ becomes **motorcycle=**
* ATV_ becoms **atv=**
* FOURWD_ becomes **4wd_only**
* SNOWMOBILE_ becomes **snowmobile=**
* SNOWSHOE_ becomes **snowwhoe=**
* XCOUNTRY_SKI_ becomes **ski**

Currently these fields appear to be empty, but that may change in the
future.

* SNOWCOACH_SNOWCAT_
* SNOWCOACH_SNOWCAT_
* E_BIKE_CLASS1_
* E_BIKE_CLASS2_
* E_BIKE_CLASS3_

This field is ignored as it's assumed the trail is accessible by
hikers.

* HIKER_PEDESTRIAN_

## Dropped Fields

These fields are dropped as unnecessary for OSM. Manye only have a
NULL value anyway, so useless.

* MOTOR_WATERCRAFT_
* NONMOTOR_WATERCRAFT_
* GIS_MILES
* Geometry Column
* TRAIL_TYPE
* TRAIL_CN
* BMP
* EMP
* SEGMENT_LENGTH
* ADMIN_ORG
* MANAGING_ORG
* SECURITY_ID
* ATTRIBUTESUBSET
* NATIONAL_TRAIL_DESIGNATION
* TRAIL_CLASS
* ACCESSIBILITY_STATUS
* TRAIL_SURFACE
* SURFACE_FIRMNESS
* TYPICAL_TRAIL_GRADE
* TYPICAL_TREAD_WIDTH
* MINIMUM_TRAIL_WIDTH
* TYPICAL_TREAD_CROSS_SLOPE
* SPECIAL_MGMT_AREA
* TERRA_BASE_SYMBOLOGY
* MVUM_SYMBOL
* TERRA_MOTORIZED
* SNOW_MOTORIZED
* WATER_MOTORIZED
* ALLOWED_TERRA_USE
* ALLOWED_SNOW_USE

## Options

	-h, --help            show this help message and exit
	-v, --verbose         verbose output
	-i INFILE, --infile INFILE input data file
	-c, --convert         Convert feature to OSM feature
	-o OUTFILE, --outfile OUTFILE Output GeoJson file

