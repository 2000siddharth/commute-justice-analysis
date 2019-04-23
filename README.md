#  Background

I was curious about the differences in commuting behavior across the US.  To
start, I looked at Los Angelinos and their communiting requirements.  I was particularly
interested in understanding whether those having lower household incomes had to
commute further and if so, how much.  Given Census data, there are many other questions
you could answer.  The LEHD Origin-Destination Employment Statistics (LODES) database
includes information on where each employee in Los Angeles commutes from (home) and
to (work).

One can easily do this with a few commands in ArcGIS but that costs money and requires
human intervention.  One could also script this, but you still have the ArcGIS license.
I then discovered QGIS, a great alternative to ArcGIS; that open source community has done an 
exceptional job.  QGIS also offers scripting, but you still need to install the 
QGIS GUI / desktop application as far as I understand.  I wanted to be able to run this
in a headless completely automated way so that it could be run in the background of any free
server; as it turns out it takes many days just to process Los Angeles, so to 
process the entire US will clearly take time.  Beyond this requirement, I also wanted to
take this opportunity to hone my Python 3+ skills and use Docker containers, so I went 
about discovering what the state of the art was wrt Python and GIS.

# What is this project?

This project is a collection of Python scripts that pre-process OpenStreetMap, US Census and
DTED data to enable shortest route, slope (cost) and other network 
analysis; identify block centroids and create street segment connectors
to the street segments and then do some cleaning of the data to enable 
route calculation.

These scripts use a combination of GDAL/OSGEO, OSMNX, shapely, and graph-tool packages to
download OpenStreetMap for the area surrounding Los Angeles, clip 
the data to a buffered Los Angeles area, calculate centroids for each census block, 
identify the nearest street lines to those centroids, then build a graph-tool network
from the street network and for each census block, calculate all the shortest path routes
that commuters from each h_geocode travel to each w_geocode identified in the LODES
database describing origin-destination for each employee in California (roughly 14M in my analysis)

Proof of concept operating in Los Angeles County to ask a few questions:

1. Commute miles in LA by category (age, pay, job classification)
2. Would there be any real cost savings to routing by elevation gain 
rather than just shortest distance.
3. Future idea - bring in traffic data and do some time-of-work optimizations
for various people combinations.

# Pieces of the Puzzle

## Census and Related Data:

* LEHD Origin-Destination Employment Statistics (LODES) - 
https://lehd.ces.census.gov/data/ downloaded from 
https://lehd.ces.census.gov/data/lodes/LODES7/ca/od/ca_od_main_JT00_2015.csv.gz
* LEHD CA Crosswalk with Census Block Metadata - 
https://lehd.ces.census.gov/data/lodes/LODES7/ca/ca_xwalk.csv.gz

## Spatial Data:
* DTED Data from https://earthexplorer.usgs.gov/ using Digital Elevation -> 
SRTM 1 Arc-Second Global data which are set at 30 meter
* Road network:  https://www.openstreetmap.org/#map=5/38.007/-95.844 - 
All roads - ran get_osm_data.py to pull down all tiles surrounding Los Angeles 
* Census blocks:  https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2016&layergroup=Blocks+%282010%29

## Setting up the Processing Environment:

Until recently, I was working with a cobbled together patchwork of 
Python packages including shapely, networkx, GDAL bindings, graph-tool
and more.  This became unwieldy as i had to upgrade packages for other
projects I was working on, started getting conflicts and maintenance was 
a real headache.   I finally caught the Docker bug which has 
significantly streamlined my environment management.  I created 
[this Dockerfile](https://github.com/CordThomas/graph-tool-docker) 
which i start with a command that mounts local files
as volumes in the container.

# Working the Questions

## Q1:  Commute miles per categories - age, pay, job classification

Assumptions:
* People commute every day
* People commute by shortest route

Approach: 

1. Prep census block data (*tl_2016_06_tabblock10.shp* with **prep_census.py**) with fields for each of the 
parameters, e.g., sa01 and sa01_CmDst for commuter distance for that classification

2. Load the origin-destination file (*ca_od_main_JT00_2014.csv*) into sqlite database 
origin destination table via **insert_data_census_od.py script** - 14,090,000 records

3. Create a census block centroid file - **create_census_centroid_points_los_angeles.py** operates on 
the census block data and creates points that are geometric centroids for only Los Angeles county.   There 
are possibly issues with that in that centroids of complex polygons are not always within the 
polygon.  That said, I think a good enough approximation.

4.  For each centroid in the area of interest, identify the nearest edge on the network
and then calculate the length to that edge and the length along the edge to end of the
edge.  Script **identify_nearest_osm_commute_node_to_centroids.py** makes these calculations
and records a record for each centroid in the nearest_street_node_info table using
the geoid of the centroid as the key and offering the end point of the edge's latitude
and longitude (lat:lon) as the key.  This is one area of simplification that reduces the 
accuracy by a small degree.  It assumes the commuter will pass through the end of
the edge along the first road they are driving rather than the start which is certainly
no more right than 50% of the time.  By applying this simplification, we have a much 
smaller problem set in the next stages.

5.  Convert the OpenStreetMap Shapefile into a graph-tool network file format (gt) via
a separate script, [Shp2Gt](https://github.com/CordThomas/shp2gt).  graph-tool appears to run
the shortest_distance algorithm [significantly faster than networkx and even faster than
iGraph](https://graph-tool.skewed.de/performance).  Graph-tool is a python wrapper to a C++
implementation.

6.  Calculate the shortest distance between each origin and destination by looping through all the
census block centroids, confirming they are part of an OD combination and then looping through
each destination to find the shortest distance between the two.   The graph-tool vertices are
identified by the lat:long key pair established in step 4 and added to the GT file in step 5.
The shortest distance is added to the distance from the centroid to the street and the length
along the street recorded in the nearest_street_node_info table.   This information is 
recorded in the commute_distances table.


Some issues about this analysis approach:

* While the OpenStreetMap data used to establish the network has directionality (oneway), this
analysis ignores that in doing the routing.
* It would be important to know the average speed on each street segment in the
morning and afternoon when people are commuting.  There don't appear to be any free
APIs with traffic / average speed data.
* This analysis assumes everyone uses surface streets and automobiles vs public transportation
or other modes such as scooters or bicycles.  