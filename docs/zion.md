# Analyzing Zion National Park Trails

As an aid to debugging my conflation software, I decided to use Zion
National Park trail data. This involved two external datasets, USGS
vector topographical maps and the National Park Service trails
dataset.The Topographical maps are in ShapeFile format, the NPS trails
is in GeoJson.

The topographical dataset has many more attributes than the NPS
dataset. For example, the topo dataset contains access information,
which is one of the goals of the [Trail Access
Project](https://wiki.openstreetmap.org/wiki/United_States/Trail_Access_Project). One
of the details I noticed was having a value of *designated* instead of
*yes* if the trail is in an official source. There are multiple access
types, horse, bicycles, etc... having them be *no* might be useless
data as it could be assumed if the access is allowed.

	"properties": {
		"highway": "path",
		"source": "National Park Service",
		"bicycle": "no",
		"atv": "no",
		"horse": "designated",
		"motorcycle": "no",
		"snowmobile": "no"
		},

## Conflating with OpenStreetMap

One big difference is that the OpenStreetMap dataset has many more
features tagged with *highway* than the other datasets. OSM has mucn
more detail, campground loop roads, service roads, 


Topo Trails 
Coalpits Wash Trail (official)
Dalton Wash Trail (BLM ?)
Huber Wash Trail (not sure)
Left Fork North Creek Trail aka Subway (official)


The Subway (Bottom) in Topo and Left Fork North Creek Trail in OSM

Pa'rus Trail is same in topo and nps, not in OSM.

Deertrap Mountain Trail, or Cable Mountain.


nps:COMMENT=062904-GPSed for cultural projects coverage
nps:EDIT_DATE=082004
nps:ED_COMMENT=063004-removed spikes from arc
nps:MILES=0.182262
