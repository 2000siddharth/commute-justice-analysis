from osgeo import ogr, osr
from grass.lib import grass

import networkx as nx
import numpy as np
import time, os
from shapely.geometry import base, point, shape
from math import sqrt
from sys import maxsize
from itertools import tee

# https://pymotw.com/2/threading/
class Streets():

#  OGRSpatialReference oSRS
#  oSRS.SetWellKnownGeogCS( "EPSG:4269" )

  def __init__(self):
    print ("INITING")
    start = time.time()
    self.SRID = 32711   # UTM zone 11S, WGS 84
    self.roadsrc = "/Users/cthomas/Development/Data/spatial/Network/streets/tl_2016_06000_roads_la_clipped.shp"
    self.blocksrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_06_tabblock10_centroids.shp"

    self.roadnetwork = ogr.Open(self.roadsrc)
    self.roadlayer  = self.roadnetwork.GetLayer(0)
    end = time.time()
    print ("Elapsed in Streets: {}".format(end-start))
    self.blocknetwork = ogr.Open(self.blocksrc)
    self.blocklayer  = self.blocknetwork.GetLayer(0)
    end = time.time()
    print ("Elapsed in Streets: {}".format(end-start))

    self.sourceSpatialRef = self.roadlayer.GetSpatialRef();
    self.targetSpatialRef = osr.SpatialReference()
    self.targetSpatialRef.ImportFromEPSG(self.SRID)

    self.transform = osr.CoordinateTransformation(self.sourceSpatialRef, self.targetSpatialRef)
    end = time.time()
    print ("Elapsed in Streets: {}".format(end-start))

#    self.roadDiGraph = nx.read_shp(self.roadsrc)
#    end = time.time()
#    print ("Elapsed in Streets: {}".format(end-start))

    print ("DONE INITING")

  def GetCountAllRoadSegments(self):
    return self.roadlayer.GetFeatureCount()

  # QGIS indicates larger distances, not sure why.  For all of W 74th Street (3 segments)
  # this program gets ~7,007 m while QGIS suggests it is 8,380 m, roughly 1.2x for each segment
  # From https://www.daftlogic.com/projects-google-maps-distance-calculator.htm
  def GetProjectedLength(self, geometry):
    geometry.Transform(self.transform)
    return geometry.Length() 

  # Reference:  http://www.gdal.org/classOGRGeometryCollection.html
  def GetLengthAllRoads(self):
    len = 0.0
    for j in range(self.GetCountAllRoadSegments()):
       roadsegment = self.roadlayer.GetFeature(j)
       roadsegmentgeom = roadsegment.GetGeometryRef()
       roadlen = self.GetProjectedLength(roadsegmentgeom)       
       len = len + roadsegmentgeom.Length()
    return len

  # Reference:
  def GetLengthRoad(self, fullname):
    len = 0.0
    self.roadlayer.SetAttributeFilter("FULLNAME = '{}'".format(fullname))
    for roadsegment in self.roadlayer:
       roadlen = self.GetProjectedLength(roadsegment.GetGeometryRef())
#        print ("Found road {} of length {}".format(roadsegment.GetField("FULLNAME"), str(roadlen)))
       len = len + roadlen
    return len

  # Given a starting point and ending point, find the 
  # shortest route using this street network.  Does not 
  # assume that the points are on the network but that
  # they are in the vicinity of the network (within 100 meters)
  def GetShortestRoute(self, srcPoint, dstPoint):
    nearest_point_on_street, nearest_street = self.GetNearestStreet(srcPoint)
    i = 0
    for n in self.roadDiGraph.edges():
       # print ("graph entry {} of type {}".format(n, type(n)))
       if i >= 10:
         break
       i = i + 1

    # shortestRoute = nx.dijkstra_path(self.roadDiGraph, (srcPoint.GetX(), srcPoint.GetY()), (dstPoint.getX(), dstPoint.GetY())) 
    # return shortestRoute

  # Following 2 methods from http://gis.stackexchange.com/a/438/94363
  # these methods rewritten from the C version of Paul Bourke's
  # geometry computations:
  # http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/
  def magnitude(self, p1, p2):
    vect_x = p2.GetX() - p1.GetX()
    vect_y = p2.GetY() - p1.GetY()
    return sqrt(vect_x**2 + vect_y**2)

  def intersect_point_to_line(self, logLevel, point, line_start, line_end):

    lineerr = 0

    try:
      line_magnitude =  self.magnitude(line_end, line_start)

      lineerr = 1
      if line_magnitude == 0:
        print("We have a 0 length magnitude for point {} to line {}, {}".format(point, line_end, line_start))
        return None

      lineerr = 3
      u = ((point.GetX() - line_start.GetX()) * (line_end.GetX() - line_start.GetX()) +
         (point.GetY() - line_start.GetY()) * (line_end.GetY() - line_start.GetY())) \
         / (line_magnitude ** 2)
    except:
      print("Error with a line magnitude of {} at line {}".format(line_magnitude, lineerr))
      return None

    if logLevel >= 2:
       print ("        We have u of {} and line_magnitude of {}".format(u, line_magnitude))

    # closest point does not fall within the line segment, 
    # take the shorter distance to an endpoint
    if u < 0.0000001 or u > 1:
      ix = self.magnitude(point, line_start)
      iy = self.magnitude(point, line_end)
      if ix > iy:
        if logLevel >= 1:
          print ("        returning Line End: {}".format(line_end))
        return line_end
      else:
        if logLevel >= 1:
          print ("        returning Line Start: {}".format(line_start))
        return line_start
    else:
      ix = line_start.GetX() + u * (line_end.GetX() - line_start.GetX())
      iy = line_start.GetY() + u * (line_end.GetY() - line_start.GetY())
      nearestPoint = ogr.Geometry(ogr.wkbPoint)
      nearestPoint.AddPoint(ix, iy)
      return nearestPoint

  # From http://stackoverflow.com/a/5764807/1723406
  # Get pairwise tuple from iterable list
  def GetPairwise (self, iteratorItems):
     a, b = tee(iteratorItems)
     next (b, None)
     return zip(a, b)

  # Convert a multilinestring to a linestring
  def ConvertMultilinestringtoLinestring(self, multilinestring):
    ls = ogr.Geometry(ogr.wkbLineString)
    for linestr in multilinestring:
      # print ("Processing MLS with line {}".format(linestr))
      for pnt in linestr.GetPoints():
        # print ("Processing MLS with point {}".format(pnt))
        ls.AddPoint(pnt[0], pnt[1])
    return ls


  # Create a copy of a shapefile, adding the new name
  # suffix at the end of the file name
  def CreateNewLayer(self, existingFile, suffix):

    inDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDataSource = inDriver.Open(existingFile, 0)
    inLayer = inDataSource.GetLayer()

    outShapeFile = existingFile.replace(".shp", suffix + ".shp")
    outDriver = ogr.GetDriverByName("ESRI Shapefile")

    # Remove output shapefile if it already exists
    if os.path.exists(outShapeFile):
        outDriver.DeleteDataSource(outShapeFile)

    # Create the output shapefile
    outDataSource = outDriver.CreateDataSource(outShapeFile)
    out_lyr_name = os.path.splitext( os.path.split( outShapeFile )[1] )[0]
    outLayer = outDataSource.CreateLayer( out_lyr_name, geom_type=ogr.wkbLineString )

    inLayerDefn = inLayer.GetLayerDefn()
    for i in range(0, inLayerDefn.GetFieldCount()):
        fieldDefn = inLayerDefn.GetFieldDefn(i)
        fieldName = fieldDefn.GetName()
        outLayer.CreateField(fieldDefn)


    return outLayer

  # Remove dangles as those street segments < dangleLength long.
  # Can't seem to find a simple method through either a spatial filter,
  # attribute filter or other means to do this in a simple call.  Seems
  # I need to iterate over every feature in the network, identify
  # those >= dangleLength and add them to a new network set...
  def RemoveDangles(self, dangleLength):

    inDriver = ogr.GetDriverByName("ESRI Shapefile")
    inDataSource = inDriver.Open(self.roadsrc, 0)
    inLayer = inDataSource.GetLayer()

    newNetworkLayer = self.CreateNewLayer(self.roadsrc, "trimmed")

    # Get the output Layer's Feature Definition
    newNetworkLayerDefn = newNetworkLayer.GetLayerDefn()

    # Add features to the ouput Layer
    for inFeature in inLayer:
        # If the feature is > dangleLength, we'll recreate it, otherwise, drop it
        featureLength = self.GetProjectedLength(inFeature.GetGeometryRef())
        if featureLength > dangleLength:
          # Create output Feature
          outFeature = ogr.Feature(newNetworkLayerDefn)

          # Add field values from input Layer
          for i in range(0, newNetworkLayerDefn.GetFieldCount()):
              fieldDefn = newNetworkLayerDefn.GetFieldDefn(i)
              fieldName = fieldDefn.GetName()

              outFeature.SetField(newNetworkLayerDefn.GetFieldDefn(i).GetNameRef(),
                  inFeature.GetField(i))

          # Set geometry as centroid
          geom = inFeature.GetGeometryRef()
          outFeature.SetGeometry(geom.Clone())
          # Add new feature to output Layer
          newNetworkLayer.CreateFeature(outFeature)
          outFeature = None
        else:
          print("We have a length of {}".format(str(featureLength)))
    # Save and close DataSources
    inDataSource = None
    outDataSource = None

  # Tried using QGIS but only supports python 2.N
  # Found this solution recommended here http://gis.stackexchange.com/a/150409/94363
  # With implementation here:  http://gis.stackexchange.com/a/81824/94363
  # Given a point, find the nearest street segment to this point
  def GetNearestStreet(self, logLevel, pntSource):

    nearest_point = None
    min_dist = maxsize
    nearest_street = None
    nearestSegment = None

    self.roadlayer.ResetReading()
    for roadsegment in self.roadlayer:
       roadGeometry = roadsegment.GetGeometryRef()

       if logLevel >= 1:
         print ("     Processing road {}".format(roadsegment.GetField("FULLNAME")))

       if roadGeometry.GetGeometryType() == ogr.wkbLineString:
         roadPointsIter = iter(roadGeometry.GetPoints())
       else:
         print ("We have a multilinestring {}".format(roadGeometry.GetGeometryName()))
         roadPointsIter = iter(self.ConvertMultilinestringtoLinestring(roadGeometry).GetPoints())
          
       for lineSegment in self.GetPairwise(roadPointsIter):

         startPoint = ogr.Geometry(ogr.wkbPoint)
         endPoint = ogr.Geometry(ogr.wkbPoint)
         startPoint.AddPoint(lineSegment[0][0], lineSegment[0][1])
         endPoint.AddPoint(lineSegment[1][0], lineSegment[1][1])

         intersection_point = self.intersect_point_to_line(logLevel, pntSource, startPoint, endPoint)

         # We didn't find an intersecting point
         if intersection_point == None:
           print ("Breakking on invalid intersection point")
           return None, None

         cur_dist = self.magnitude (pntSource, intersection_point)

         if logLevel >= 1:
           print ("       Processing lineSegment {} with cur_dist {}".format(lineSegment, cur_dist))

         if cur_dist < min_dist:
           min_dist = cur_dist
           nearest_point = intersection_point
           nearest_street = roadsegment
           nearestSegment = lineSegment
           if logLevel >= 1:
             print ("     Setting min_dist et all from road {} at intersection {} and nearest_point {} with cur_dist {} updating min_dist {}".format(roadsegment.GetField("FULLNAME"), intersection_point, nearest_point, cur_dist, min_dist))

    if logLevel >= 1:
      print ("    Nearest point for {} found at {} from lineSegment {} with a min_dist {}".format(pntSource, nearest_point, nearestSegment, min_dist))
    return nearest_point, nearest_street

  def ExtendLine (self, startPoint, endPoint, length):
    lenAB = sqrt(pow(startPoint.GetX() - endPoint.GetX(), 2.0) + pow(startPoint.GetY() - endPoint.GetY(), 2.0))
    newPoint = ogr.Geometry(ogr.wkbPoint)
    newPoint.AddPoint( endPoint.GetX() + (endPoint.GetX() - startPoint.GetX()) / lenAB * length,
                       endPoint.GetY() + (endPoint.GetY() - startPoint.GetY()) / lenAB * length)

    return newPoint

  # Given a source point feature, find the streets that are closest
  # to that point, starting a 100 meters, moving out until a set
  # can be found.  
  # Create a buffer using Shapely, then convert to an osgeo Polygon,
  # then perform a spatial filter to return a set of nearby streets.
  def FilterNearbyStreets (self, logLevel, pntSource):

    if logLevel == 1:
      print ("Point source X and Y: {}, {}".format(str(pntSource.GetX()), str(pntSource.GetY())))
    
    shpPoint = point.Point(pntSource.GetX(), pntSource.GetY())
    
    enoughSegments = False
    bufferSize = 0.001

    while (enoughSegments != True):
      buffer = shpPoint.buffer(bufferSize)

      if logLevel == 1:
        if bufferSize > 0.001:
          print ("We're at buffer size {} for {}".format(bufferSize, pntSource))

      ring = ogr.Geometry(ogr.wkbLinearRing)
      for bufferedPoint in list(buffer.exterior.coords):
        ring.AddPoint(bufferedPoint[0], bufferedPoint[1])
      ogrPoly = ogr.Geometry(ogr.wkbPolygon)
      ogrPoly.AddGeometry(ring)
      self.roadlayer.SetSpatialFilter(ogrPoly)

      enoughSegments = (self.roadlayer.GetFeatureCount() > 1)
      bufferSize = bufferSize + 0.0005

      if logLevel == 1:
        for feature in self.roadlayer:
          print("    Feature street name: {}".format(feature.GetField("FULLNAME")))
