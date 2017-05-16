A collection of Python scripts that pre-process open street map, census and
DTED data to enable shortest route, slope (cost) and other network 
analysis. 

Using a combination of GDAL, shapely, networkx and possibly GRASS packages
to get nearest lines to points, project lines onto points, break lines at
intersections, remove dangles and other operations possible in QGIS, ArcGIS 
and other GUI-based desktop applications, working to build a completely
automated and free system for doing some basic network analysis such
as routing optimization in Python.

Proof of concept operating in Los Angeles County to ask a few questions:

1. Commute miles in LA by category (age, pay, job classification)
2. Would there be any real cost savings to routing by elevation gain 
rather than just shortest distance.
