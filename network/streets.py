from osgeo import ogr, osr
import networkx as nx
import geopandas as gp
import pandas as pd
import time, os
import configparser
import fiona
from shapely.geometry import Point, shape
from math import sqrt
from sys import maxsize, float_info
import shutil
from itertools import tee

# https://pymotw.com/2/threading/
class Streets(object):

#  OGRSpatialReference oSRS
#  oSRS.SetWellKnownGeogCS( "EPSG:4269" )

  def __init__(self, street_network_src = None):

    print("INITING STREET NETWORK {}".format(os.getcwd()))

    config = configparser.ConfigParser()
    config.read(os.getcwd() + '/params.ini')

    # 32711 is 11S, 26911 is 11N
    # 26945 is California NAD83 Zone 5
    self.SRID = 26945  # UTM zone 11N, WGS 84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(self.SRID)
    self.spatialRef = srs

    if (street_network_src == None):
      self.roadsrc = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL'][
        'LA_Street_Centerlines_Block_Connectors'] + '.shp'
    else:
      self.roadsrc = street_network_src

    self.roadnetwork = ogr.Open(self.roadsrc)
    self.roadlayer = self.roadnetwork.GetLayer(0)

    self.blocksrc = config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] + config['SPATIAL']['Census_Block10_Centroids'] + '.shp'
    self.blocknetwork = ogr.Open(self.blocksrc)
    self.blocklayer = self.blocknetwork.GetLayer(0)

    self.sourceSpatialRef = self.roadlayer.GetSpatialRef()
    self.targetSpatialRef = osr.SpatialReference()
    self.targetSpatialRef.ImportFromEPSG(self.SRID)

    self.transform = osr.CoordinateTransformation(self.sourceSpatialRef, self.targetSpatialRef)

    print("DONE INITING ")

  @classmethod
  def init_with_layer (cls, layer_src):
    return cls(layer_src)

  @classmethod
  def init_default(cls):
    return cls()

  def GetCountAllRoadSegments(self):
    return self.roadlayer.GetFeatureCount()

  # QGIS indicates larger distances, not sure why.  For all of W 74th Street (3 segments)
  # this program gets ~7,007 m while QGIS suggests it is 8,380 m, roughly 1.2x for each segment
  # From https://www.daftlogic.com/projects-google-maps-distance-calculator.htm
  def GetProjectedLength(self, geometry):
    geometry.Transform(self.transform)
    return geometry.Length()

  def TransformShape(self, geometry):
    new_geometry = geometry.Clone()
    new_geometry.Transform(self.transform)
    return new_geometry

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

  def CalcWeightFromMTFCC(self, MTFCC, EdgeLength):

    if (MTFCC == "S1100"):
      return 1.0 * EdgeLength
    elif(MTFCC == "S1200"):
      return 1.2 * EdgeLength
    elif (MTFCC == "S1400"):
      return 1.6 * EdgeLength
    else:
      return 1.5 * EdgeLength

  def InitNetworkGraphSimple(self):

      start = time.time()

      self.roadGraph = nx.read_shp(self.roadsrc, False)
      self.StreetNodeFromDict = {}
      self.StreetNodeToDict = {}

      print("Graph has been successfully generated{}".format(nx.info(self.roadGraph)))
      print("Show graph data structure EDGE".format(self.roadGraph.get_edge_data(*list(self.roadGraph.edges())[0])))
      print("Show graph data structure NODE".format(list(self.roadGraph.nodes())[0]))
      for edge in self.roadGraph.edges(data=True):
        self.StreetNodeFromDict[edge[0]] = (edge[0], edge[1])
        self.StreetNodeToDict[edge[1]] = (edge[0], edge[1])

      # Now we replicate and make undirected
      self.roadGraph = self.roadGraph.to_undirected(reciprocal=False)

#      for edge in self.roadGraph.edges(data=True):

      end = time.time()
      print("Network:  ")
      print("Elapsed in Streets InitNetwork: {}".format(end - start))

  # Posts read on this topic:
  # https://gis.stackexchange.com/questions/213369/how-to-calculate-edge-length-in-networkx
  # https://gis.stackexchange.com/questions/211053/inaccurate-output-missing-features-while-reading-a-shapefile-into-networkx/211103#211103
  # Cribbed Shape to DiGraph conversion here:  https://stackoverflow.com/questions/46114754/osmnx-and-networkx-shortest-path-length-and-edge-attributes
  def InitNetworkGraphPandas(self):

    start = time.time()

    self.StreetDataFrame = gp.read_file(self.roadsrc)

    # Compute the start- and end-position based on linestring
    self.StreetDataFrame['Start_pos'] = self.StreetDataFrame.geometry.apply(lambda x: x.coords[0])
    self.StreetDataFrame['End_pos'] = self.StreetDataFrame.geometry.apply(lambda x: x.coords[-1])
    print ("\n\nSet Start and End Pos Series")
    print(self.StreetDataFrame.head())

    self.StreetDataFrame['length'] = self.StreetDataFrame.geometry.apply(lambda x: x.length)
    self.StreetDataFrame['weight'] = self.StreetDataFrame.apply(lambda x: self.CalcWeightFromMTFCC(x['MTFCC'], x['length']), axis=1)

    print ("\n\nSet Length and Weight")
    print(self.StreetDataFrame.head())

    # Create Series of unique nodes and their associated position
    s_points = self.StreetDataFrame.Start_pos.append(self.StreetDataFrame.End_pos).reset_index(drop=True)
    s_points = s_points.drop_duplicates()

    print ("\n\ns_points is of type {}".format(type(s_points)))

    # Add index of start and end node of linestring to geopandas DataFrame
    df_points = pd.DataFrame(s_points, columns=['Start_pos'])
    df_points['FNODE_'] = df_points.index
    self.StreetDataFrame = pd.merge(self.StreetDataFrame, df_points, on='Start_pos', how='inner')

    df_points = pd.DataFrame(s_points, columns=['End_pos'])
    df_points['TNODE_'] = df_points.index
    self.StreetDataFrame = pd.merge(self.StreetDataFrame, df_points, on='End_pos', how='inner')

    # Bring nodes and their position in form needed for osmnx (give arbitrary osmid (index) despite not osm file)
    df_points.columns = ['pos', 'osmid']
    df_points[['x', 'y']] = df_points['pos'].apply(pd.Series)
    df_node_xy = df_points.drop('pos', 1)

    self.roadGraph = nx.MultiDiGraph(name="LA_Roads")

    node_index = 0
    for node, data in df_node_xy.T.to_dict().items():
        self.roadGraph.add_node(node, **data)
        node_index += 1
        if (node_index % 10000 == 0):
          print(node)
          print(', '.join(['{}={!r}'.format(k, v) for k, v in data.items()]))

    # Add edges to graph
    node_index = 0
    for i, row  in self.StreetDataFrame.iterrows():
        dict_row  = row.to_dict()
        if 'geometry' in dict_row: del dict_row['geometry']
        self.roadGraph.add_edge(u=dict_row['FNODE_'], v=dict_row['TNODE_'], **dict_row)
        node_index += 1
        if (node_index % 10000 == 0):
          print(dict_row['FNODE_'])
          print(', '.join(['{}={!r}'.format(k, v) for k, v in dict_row.items()]))

    # Now reverse the F and T nodes and add all new edges so we have a bi-directional
    # graph.  Without this, the network traversal will only try to from FNODES to TNODES
    # which is like assuming all streets in the network are one-way in the direction
    # they were digitized.  This may be the case in some LA Streets, we just don't
    # have that data, so assuming all two-way streets for now.
    self.StreetDataFrame.rename(columns={'Start_pos': 'End_pos',
           'End_pos': 'Start_pos',
           'FNODE_': 'TNODE_',
           'TNODE_': 'FNODE_', }, inplace=True)

    # Add edges to graph
    for i, row  in self.StreetDataFrame.iterrows():
        dict_row  = row.to_dict()
        if 'geometry' in dict_row: del dict_row['geometry']
        self.roadGraph.add_edge(u=dict_row['FNODE_'], v=dict_row['TNODE_'], **dict_row)

    # self.StreetDataFrame.to_csv("/Users/cthomas/Development/roeda/dataframe.csv")
    # nx.write_shp(self.roadGraph, "/Users/cthomas/Development/roeda/")
    print("Graph has been successfully generated{}".format(nx.info(self.roadGraph)))
    print("Show graph data structure EDGE".format(self.roadGraph.get_edge_data(*list(self.roadGraph.edges())[0])))
    print("Show graph data structure NODE".format(list(self.roadGraph.nodes())[0]))
    with open("/Users/cthomas/Development/roeda/weighted_edge_list.txt", "w") as writeit:
      for edge in self.roadGraph.edges(data=True):
        writeit.write("{}\n".format(edge))

    end = time.time()
    print ("Network:  ")
    print ("Elapsed in Streets InitNetwork: {}".format(end-start))

  def GetStreetIDFromNodeSimple(self, geometry_point, FromOrTo = 'FNODE_'):

    if (FromOrTo == "FNODE_"):
      if geometry_point in self.StreetNodeFromDict:
        return self.StreetNodeFromDict[geometry_point]
      else:
        return -1
    else:
      return self.StreetNodeToDict[geometry_point]

  def GetNodeID(self, geometry_point, FromOrTo = 'FNODE_'):

    if (FromOrTo == "FNODE_"):
      frame_position = "Start_pos"
    else:
      frame_position = "End_pos"

    print("      Looking for frame pos {} with a geometry of {}".format(frame_position, geometry_point))

    find_record = self.StreetDataFrame.loc[self.StreetDataFrame[frame_position] == geometry_point]
    print ("      GET NODE Record of type {} has FNODE type {} and values {}".format(type(find_record), type(find_record[FromOrTo]),
                                                                                     find_record[FromOrTo].values))
    if (find_record.empty):
      return -1
    else:
      return find_record[FromOrTo].iloc[0]

  def CalculateShortestRoute(self, srcPoint, dstStreetSegmentID):
    """
    Given a starting point and ending point, find the
    shortest route using this street network.  Does not
    assume that the points are on the network but that
    they are in the vicinity of the network (within 100 meters)

    Parameters
    ----------
    srcPoint : osgeo.ogr.Geometry
      The origin of the route as an osgeo Point Geometry
    dstPointID : The network ID of the destination point
      The destination of the route.  This is passed rather than
      determined each time as it is expected the calling
      method is looping over mulitple origins for each
      destination.

    Returns
    -------
    The ID of the route which is the path to the shapefile generated.
    """
    srcSegmentID = self.GetStreetIDFromNodeSimple(srcPoint, "FNODE_")

    # print ("    The home {} work {} IDs have been identified".format(srcSegmentID, dstStreetSegmentID))
    if (srcSegmentID != -1 and dstStreetSegmentID != -1):

      start = time.time()
      try:
        shortestRoute = self.roadGraph.subgraph(nx.shortest_path(self.roadGraph, srcSegmentID[0], dstStreetSegmentID[0], weight='weight'))
        end = time.time()
        # print ("Elapsed in Streets GetShortestRoute: {}".format(end-start))
        nx.write_shp(shortestRoute, str(srcSegmentID[0]) + "-" + str(dstStreetSegmentID[0]))
        return str(srcSegmentID[0]) + "-" + str(dstStreetSegmentID[0])
      except nx.NetworkXNoPath:
        print ("---- We could not find a path from {}".format(srcPoint))
        return None
    else:
      print ("**** We could not find the street connector for {}".format(srcPoint))
      return None

  def MergeShortestRoute(self, route_id):

    """
    Merges the calculated route with the shortest route returning
    the length in the current coordinate system (degrees). It merges
    the two shape files and then removes the original.  The first
    call to this method sets up the shortest route by copying
    the first calculated route.  All fields should be identical.

    Parameters
    ----------
    route_id : string
      The from-to coordinate pair of the route which defines
      the path to the route shapefile

    Returns
    -------
    The length of the route that was merged.
    """
    routes_path = "shortest_routes"

    path_length = 0

    if not os.path.exists(routes_path + "/edges.shp"):
      if os.path.exists(routes_path):
        os.rmdir(routes_path)
      shutil.copytree(route_id, routes_path)
    else:
      meta = fiona.open(routes_path + '/edges.shp').meta
      with fiona.open(routes_path + '/edges.shp', 'a', **meta) as output:
        for feature in fiona.open(route_id + '/edges.shp'):
          # length is in degrees; a degree in LA ranges from ~9,400 meters to
          # the north and 9,200 meters to the south
          path_length += shape(feature['geometry']).length
          output.write(feature)

      meta = fiona.open(routes_path + '/nodes.shp').meta
      with fiona.open(routes_path + '/nodes.shp', 'a', **meta) as output:
        for feature in fiona.open(route_id + '/nodes.shp'):
          output.write(feature)

      shutil.rmtree(route_id)

      return path_length

  # Calculate the distance from p1 and p2
  # Following 2 methods from http://gis.stackexchange.com/a/438/94363
  # these methods rewritten from the C version of Paul Bourke's
  # geometry computations:
  # http://local.wasp.uwa.edu.au/~pbourke/geometry/pointline/
  def DistanceBetweenPoints(self, p1, p2):
    vect_x = p2.GetX() - p1.GetX()
    vect_y = p2.GetY() - p1.GetY()
    return sqrt(vect_x**2 + vect_y**2)

  def intersect_point_to_line(self, logLevel, point, line_start, line_end):

    lineerr = 0

    try:
      line_DistanceBetweenPoints =  self.DistanceBetweenPoints(line_end, line_start)

      lineerr = 1
      if line_DistanceBetweenPoints == 0:
        print("We have a 0 length DistanceBetweenPoints for point {} to line {}, {}".format(point, line_end, line_start))
        return None

      lineerr = 3
      u = ((point.GetX() - line_start.GetX()) * (line_end.GetX() - line_start.GetX()) +
         (point.GetY() - line_start.GetY()) * (line_end.GetY() - line_start.GetY())) \
         / (line_DistanceBetweenPoints ** 2)
    except:
      print("Error with a line DistanceBetweenPoints of {} at line {}".format(line_DistanceBetweenPoints, lineerr))
      return None

    if logLevel >= 2:
       print ("        We have u of {} and line_DistanceBetweenPoints of {}".format(u, line_DistanceBetweenPoints))

    # closest point does not fall within the line segment,
    # take the shorter distance to an endpoint
    if u < 0.0000001 or u > 1:
      ix = self.DistanceBetweenPoints(point, line_start)
      iy = self.DistanceBetweenPoints(point, line_end)
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
    if (multilinestring.GetGeometryType() == ogr.wkbLineString):
        return multilinestring
    else:
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

  def within(self, p, q, r):
    "Return true iff q is between p and r (inclusive)."
    return p <= q <= r or r <= q <= p

  def isBetween(self, a, b, c):
    crossproduct = (c.GetY() - a.GetY()) * (b.GetX() - a.GetX()) - (c.GetX() - a.GetX()) * (b.GetY() - a.GetY())

    # compare versus epsilon for floating point values, or != 0 if using integers
    if abs(crossproduct) > float_info.epsilon:
      return False

    dotproduct = (c.GetX() - a.GetX()) * (b.GetX() - a.GetX()) + (c.GetY() - a.GetY()) * (b.GetY() - a.GetY())
    if dotproduct < 0:
      return False

    squaredlengthba = (b.GetX() - a.GetX()) * (b.GetX() - a.GetX()) + (b.GetY() - a.GetY()) * (b.GetY() - a.GetY())
    if dotproduct > squaredlengthba:
      return False

    return True

  def IsPointInBetween(self, pntFirst, pntSecond, pntTest):
    """A simplified version of cross-product evaluation of whether a point
    is on a line.  Compares the slope of the line to the slopes of the
    lines that would be created between the test point and the lines two
    nodes within a certain tolerance and then verifies that the point
    is within the bounding box of the line."""

    if (pntFirst.GetX() == pntTest.GetX() or pntSecond.GetX() == pntTest.GetX()):
      return True

    line_slope = abs((pntSecond.GetY() - pntFirst.GetY()) / (pntSecond.GetX() - pntFirst.GetX()))
    test_slope_start = abs((pntFirst.GetY() - pntTest.GetY()) / (pntFirst.GetX() - pntTest.GetX()))
    test_slope_end = abs((pntTest.GetY() - pntSecond.GetY()) / (pntTest.GetX() - pntSecond.GetX()))

    delta_start = abs(line_slope - test_slope_start)
    delta_end = abs(line_slope - test_slope_end)

    # print("        Line slope {} slope end {}\ndelta "
    #       "start {} delta end {}".format(line_slope, test_slope_start, delta_start, delta_end))

    # if ((delta_start < 0.2 and delta_end < 0.2) and
    #   (delta_start > 0.05 and delta_end > 0.05)):
    #   print("   ----- We have a delta > 0.05 and < 0.2")

    return ((delta_start < 0.05 and delta_end < 0.05)
      and (self.within (pntFirst.GetX(), pntTest.GetX(), pntSecond.GetX())
      and self.within (pntFirst.GetY(), pntTest.GetY(), pntSecond.GetY())))

  def GetStartAndEndVertices(self, edge, i):

    pointStart = ogr.Geometry(ogr.wkbPoint)
    pointStart.AddPoint(edge.GetPoint(i)[0], edge.GetPoint(i)[1])
    pointEnd = ogr.Geometry(ogr.wkbPoint)
    pointEnd.AddPoint(edge.GetPoint(i+1)[0], edge.GetPoint(i+1)[1])

    return pointStart, pointEnd

  def GetLengthFromMidpointToEnd(self, edge, midPoint):
    """Given an edge with 2 or more vertices, find the length
      of an arbitrary point on that line to the end.  Iterate
      through each of the vertices in the edge, find the two
      vertices that bookend the midpoint and then calculate
      the length from that midpoint to the next vertex and
      add that to all remaining line segments.

      It also returns the coordinates of the end nodes vertex."""

    length = 0.0
    lat_long = ''

    midPoint.Transform(self.transform)
    edge.Transform(self.transform)

    # print("    We have an edge {}".format(edge))

    if (len(edge.GetPoints()) == 0):
      pointStart, pointEnd = self.GetStartAndEndVertices(edge, 0)
      length = self.DistanceBetweenPoints(pointStart, pointEnd)
    else:
      in_the_line = False
      count_points = edge.GetPointCount()
      for i in range(0, count_points - 1):
        pointStart, pointEnd = self.GetStartAndEndVertices(edge, i)
        isBetween = self.IsPointInBetween(pointStart, pointEnd, midPoint)
        # print("    We are between {} for Start {}\n Mid {}\n End {}".format(isBetween, pointStart, midPoint, pointEnd))
        if not in_the_line and isBetween:
          length = self.DistanceBetweenPoints(midPoint, pointEnd)
          in_the_line = True
        else:
          if (in_the_line):
            length += self.DistanceBetweenPoints(pointStart, pointEnd)

        if (i == count_points - 2):
          lat_long = str(pointEnd.GetX()) + ":" + str(pointEnd.GetY())

    return length, lat_long

  # Given a point lying near in the vicinity of edges in a network,
  # fidn the nearest edge to that point and return the distance to that
  # edge and the edge feature.
  # Found this solution recommended here http://gis.stackexchange.com/a/150409/94363
  # With implementation here:  http://gis.stackexchange.com/a/81824/94363
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

         cur_dist = self.DistanceBetweenPoints (pntSource, intersection_point)

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

  def ExtendLine (self, log_level, startPoint, endPoint, length):
    lenAB = sqrt(pow(startPoint.GetX() - endPoint.GetX(), 2.0) + pow(startPoint.GetY() - endPoint.GetY(), 2.0))
    if (log_level >= 1):
      print("We have a lenAB of {}".format(lenAB))
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

    shpPoint = Point(pntSource.GetX(), pntSource.GetY())

    enoughSegments = False
    bufferSize = 0.001

    while (enoughSegments != True):

      if logLevel == 1:
        print ("About to buffer {} of size {}".format(shpPoint, bufferSize))

      buffer = shpPoint.buffer(bufferSize)

      if logLevel == 1:
        if bufferSize >= 0.001:
          print ("We're at buffer size {} for {}".format(bufferSize, pntSource))

      ring = ogr.Geometry(ogr.wkbLinearRing)
      for bufferedPoint in list(buffer.exterior.coords):
        ring.AddPoint(bufferedPoint[0], bufferedPoint[1])
      ogrPoly = ogr.Geometry(ogr.wkbPolygon)
      ogrPoly.AddGeometry(ring)
      # print ("About to set spatial filter")
      self.roadlayer.SetSpatialFilter(ogrPoly)
      # print ("Set spatial filter!")

      enoughSegments = (self.roadlayer.GetFeatureCount() > 1)
      bufferSize = bufferSize + 0.0005

      if logLevel == 1:
        for feature in self.roadlayer:
          print("    Feature street name: {}".format(feature.GetField("FULLNAME")))
