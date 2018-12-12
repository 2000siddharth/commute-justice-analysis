#  Background

I was curious about the differences in commuting behavior across the US.  To
start, I looked at Los Angelinos and their communiting habits.  I was particularly
interested in understanding whether those having lower household incomes had to
commute more and if so, how much.  Given Census data, there are many other questions
you could answer.

One can easily do this with a few commands in ArcGIS but that costs money and requires
human intervention.  One could also script this, but you still have the ArcGIS license.
I then discovered QGIS, a great alternative to ArcGIS; that team have done an 
exceptional job.  QGIS also offers scripting, but you still need to install the 
QGIS GUI / desktop application as far as I understand.  I wanted to be able to run this
in a headless completely automated way so that it could be run in the background of any free
server; as it turns out it takes many hours just to process Los Angeles, so to 
process the entire US will clearly take time.  Beyond this requirement, I also wanted to
take this opportunity to hone my Python 3+ skills, so I went about discovering what the state
of the art was wrt Python and GIS.

# What is this project?

This project is a collection of Python scripts that pre-process open street map, census and
DTED data to enable shortest route, slope (cost) and other network 
analysis; identify block centroids and create street segment connectors
to the street segments and then do some cleaning of the data to enable 
route calculation.

These scripts use a combination of GDAL/OSGEO, shapely and networkx packages
to get nearest lines to points, project lines onto points, break lines at
intersections, remove dangles and other operations possible in QGIS, ArcGIS 
and other GUI-based desktop applications, working to build a completely
automated and free system for doing some basic network analysis such
as routing optimization in Python.

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
* Road network:  https://www.census.gov/cgi-bin/geo/shapefiles/index.php - 
All roads - ran getstreets.py to pull down all counties in California 
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

4.  For each origin/destination, find the shortest distance to a street and created new lines 
from census block centroids to the road network (**connect_block_centroids_to_nearest_streets_extended.py**).  This 
writes to a csv file with the start and end coordinates.  This operates on the *tl_2016_06_tabblock10_centroids*
shapefile created in the previous step.  ***PreProcessBlockCentroidStreetLines*** 
creates a segment CSV with the LINESTRING definition of the segment connecting the 
block centroid to the nearest street.  

5.  Next we merge the centroid connectors with the clipped LA county street segments, 
*tl_2016_06000_roads_la_clipped* by creating a shapefile out of the LINESTRING CSV created 
in the previous step.  We run **union_streets_connectors.py** with option 4 to execute step 1,
convert CSV to shapefile (result street_segment_block_centroid_connectors_extend.shp), step 2, 
intersect the centroid connectors to the streets (result tl_2016_06000_roads_la_clipped_extended.shp), 
and step 3 merging the streets and centroids from step 2 with the remaining streets (those not 
intersected by centroid connectors) (result tl_2016_06000_roads_la_clipped_extended.shp again).  
Validated this works via QGIS by running a few examples of the network road graph method.

6. To create an routable network, need to split all street segments so there are nodes
at each intersecting point.   Run SplitLinesWithLines' split_lines_with_lines method
with the same source as both network A and B.  This largely uses the Shapely intersect
and split methods to get the job done.  Can result in a 5-10x network size (# edges).

7. To support the analysis of weight-based networks, we need an attribute in the network
that represents the cost of that segment.  Run **add_length_weight.py** to populate a
distance_weight field with the length of the edge.

8.  Now the fun starts - run **calculate_shortest_routes.py** which creates an undirected
networkx graph, loops over each origin-destination to calculate the total commute distance
for each block in the study area, writing this distance to a SQLite table, commute_distances. 