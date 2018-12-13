from osgeo import ogr
from osgeo import osr
import csv
from math import sqrt
import sys
import configparser, os
from shapely.geometry import Point
from shapely.wkt import loads
from census.census_block_centroids_sp import CensusBlockCentroids
from census.origin_destination_db import OriginDestinationDB

# Intersect the census provided streets with the census block centroid street connectors
# http://gdal.org/python/osgeo.ogr.Layer-class.html#Union

# Created this test to validate why a connector did not split a street
# on Union - turns out the street abutted but did not cross the connector.
def TestCrossing():
    line1 = ogr.Geometry(ogr.wkbLineString)
    line1.AddPoint(-118.348132334411,33.8344022181848)
    # line1.AddPoint(-118.348571272395,33.833726580714)
    line1.AddPoint(-118.3486,33.833726580714)

    line2 = ogr.Geometry(ogr.wkbLineString)
    line2.AddPoint(-118.349320377112,33.833718080868)
    line2.AddPoint(-118.348876,33.833728)
    line2.AddPoint(-118.348571,33.833727)

    print ('Line 1 and 2 Intersect: {}'.format(line1.Intersects(line2)))

# From https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-a-new-shapefile-and-add-data
# To abstract this to any CSV, would want to:
#   add arguement for coordinate spatial reference
#   read shapetype from first field's WKT value (POINT, LINESTRING) and convert to ogr
#   iterate over fields in CSV to add to fields in Shapefile
def CreateShapeFromCSV(csvFileName):

  print ('Creating shape from CSV {} as {}'.format(csvFileName, csvFileName.replace('.csv', '.shp')))
  reader = csv.DictReader(open(csvFileName, 'rt'),
                          delimiter='\t',
                          quoting=csv.QUOTE_MINIMAL)

  driver = ogr.GetDriverByName('ESRI Shapefile')
  data_source = driver.CreateDataSource(csvFileName.replace('.csv', '.shp'))

  # create the spatial reference, WGS84
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  # create the layer
  print('About to create layer')
  layer = data_source.CreateLayer(csvFileName.replace('.csv', ''), srs, ogr.wkbLineString)

  field_name = ogr.FieldDefn('GeoID', ogr.OFTString)
  field_name.SetWidth(16)
  layer.CreateField(field_name)

  n = 0
  print('About to iterate over CSV')
  for row in reader:
    # create the feature
    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    feature.SetField('GeoID', row['GeoID'].replace('\'', ''))

    # Create the point from the Well Known Txt
    linestring = ogr.CreateGeometryFromWkt(row['Geometry'])
    feature.SetGeometry(linestring)
    # Create the feature in the layer (shapefile)
    layer.CreateFeature(feature)
    # Dereference the feature
    feature = None

    n = n + 1

  # Save and close the data source
  data_source = None

  print ('Processed {} segments'.format(str(n)))

def CountLayerFeatures(layer):
  featureCount = layer.GetFeatureCount()
  print ('There are {} features in {}'.format(str(featureCount), layer.GetName()))

# Convert a multilinestring to a linestring
def ConvertMultilinestringtoLinestring(multilinestring):

    if (multilinestring.GetGeometryType() == ogr.wkbLineString):
        return multilinestring
    else:
        ls = ogr.Geometry(ogr.wkbLineString)
        for linestr in multilinestring:
            # print ('Processing MLS with line {}'.format(linestr))
            for pnt in linestr.GetPoints():
                # print ('Processing MLS with point {}'.format(pnt))
                ls.AddPoint(pnt[0], pnt[1])

        return ls

def SetCensusRoadProperties (source_feature, new_feature):
    new_feature.SetField('FULLNAME', source_feature.GetField('FULLNAME'))
    new_feature.SetField('LINEARID', source_feature.GetField('LINEARID'))
    new_feature.SetField('MTFCC', source_feature.GetField('MTFCC'))
    new_feature.SetField('RTTYP', source_feature.GetField('RTTYP'))


def IsDangle (line_geometry, dangle_length):
    return line_geometry.Length() <= (dangle_length + dangle_length / 10) and \
           line_geometry.Length() >= (dangle_length - dangle_length / 10)

def LineSegmentCount(line_geometry_list):
    line_count = 0
    for street_line in line_geometry_list:
        line_count += 1
    return line_count

def ExtendLine (street_segment_geom, at_start, start_point_tup, end_point_tup, length):

    start_point = ogr.Geometry(ogr.wkbPoint)
    end_point = ogr.Geometry(ogr.wkbPoint)
    start_point.AddPoint(start_point_tup[0], start_point_tup[1])
    end_point.AddPoint(end_point_tup[0], end_point_tup[1])
    lenAB = sqrt(pow(start_point.GetX() - end_point.GetX(), 2.0) + pow(start_point.GetY() - end_point.GetY(), 2.0))
    newPoint = ogr.Geometry(ogr.wkbPoint)
    newPoint.AddPoint( end_point.GetX() + (end_point.GetX() - start_point.GetX()) / lenAB * length,
                       end_point.GetY() + (end_point.GetY() - start_point.GetY()) / lenAB * length)

    extended_line = ogr.Geometry(ogr.wkbLineString)
    # Add this newly extended point as either the first point on the LINESTRING or the last
    if (at_start):
        extended_line.AddPoint(newPoint.GetX(), newPoint.GetY())
    for i in range(0, street_segment_geom.GetPointCount()):
        extended_line.AddPoint(street_segment_geom.GetPoint(i)[0], street_segment_geom.GetPoint(i)[1])
    if (not at_start):
        extended_line.AddPoint(newPoint.GetX(), newPoint.GetY())

    return extended_line

def LineNodeIndexInConnector(street_segment_geom, conector_segment_geom):
    '''
    Determine whether a node in the street_segment_geom is within
    the buffer of the connector_segment_geom.  If so, return the
    index of the Points on the line that is within the buffer.

    Parameters
    ----------
        street_segment_geom : LineString Geometry
            The main street segment on which we are looking for
            the end node that is near the connector segment.
        conector_segment_geom : LineString Geometry
    :return:
    '''

    buffered_connector = conector_segment_geom.Buffer(0.0000001)
    for i in range(0, street_segment_geom.GetPointCount()):
        # print ('  Looking at index {}'.format(str(i)))
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(street_segment_geom.GetPoint(i)[0],street_segment_geom.GetPoint(i)[1])
        if point.Within(buffered_connector):
            print('  We found the index {}'.format(str(i)))
            return i

    return -1

def ConvertMultiLinetoLineString(street_segment_geom):

    if (street_segment_geom.GetGeometryType() == ogr.wkbLineString):
        return street_segment_geom
    else:
        return ConvertMultilinestringtoLinestring(street_segment_geom)

def ExtendStreetStreetSegment(street_segment_geom, connector_segment_geom):

    # print ('     The street segment {}\n      The connector segment {}'.format(street_segment_geom,
    #                                                                            connector_segment_geom))
    # is one of the line nodes in the connector buffer, we'll extend that end of the line
    line_node_index = LineNodeIndexInConnector(street_segment_geom, connector_segment_geom)
    if (line_node_index > -1):
        if (line_node_index == 0):
            start_point = street_segment_geom.GetPoint(1)
            end_point = street_segment_geom.GetPoint(0)
        else:
            start_point = street_segment_geom.GetPoint(line_node_index - 1)
            end_point = street_segment_geom.GetPoint(line_node_index)

        street_segment_geom = ExtendLine(street_segment_geom,
                                         (line_node_index == 0),
                                         start_point, end_point, 0.0000002)
        return street_segment_geom

    return None

def CopyFeature (source_feature, target_layer, target_layerDefn, origin = -1):

    new_feature = ogr.Feature(target_layerDefn)
    if (source_feature is not None):
      if (source_feature.GetDefnRef().GetFieldIndex('LINEARID') != -1) :
          SetCensusRoadProperties(source_feature, new_feature)
      else:
          new_feature.SetField('GeoID', source_feature.GetField('GeoID'))

      new_feature.SetGeometry(source_feature.GetGeometryRef())
      # PrintFeatureFields(target_layer, new_feature)
      target_layer.CreateFeature(new_feature)
      new_feature = None

def CreateFeatures(census_street_feature, merged_layer, merged_layer_defn,
                   geo_id, census_street_geom, total_count):
    '''
    Creates new features in the merged layer assuming that a Union happened
    and that we have one or more census block connectors split at the street
    lines along with split street lines.  The census_street_geom is going to
    be a MULTILINESTRING (check for that) which will first have a set of
    LINESTRINGs that are the split street lines and then a set of
    LINESTRINGs that are the split block centroid connectors with a dangle

    Arguments
    ----------
    census_street_feature : osgeo.ogr.Feature
      The street centerline feature where we pull the attributes to assign
      to the split segments
    merged_layer : osgeo.ogr.Layer
      The layer we are merging the streets and connectors into
    merged_layer_defn: osgeo.ogr.FeatureDefn
      The feature definition including fields and such
    geo_id : string
      The processing connetor's geoID
    census_street_geom : osgeo.ogr.Geometry
      The geometry of the unioned street segments, should be a MULTILINESTRING.
      See method description for more on this.
    Returns
    -------
    None
    '''

    line_count = 1
    connector_count = 0
    total_line_seg_count = LineSegmentCount(census_street_geom)
    new_feature = ogr.Feature(merged_layer_defn)
    for street_line in census_street_geom:
        # print ('  Geometry Feature Count {} for {}'.format(str(line_count), geo_id))
        process_line = False
        if  (line_count <= total_line_seg_count / 2):
            if not IsDangle(street_line, 0.0000005):
              SetCensusRoadProperties(census_street_feature, new_feature)
              new_feature.SetField('GeoID', geo_id)
              new_feature.SetField('TRACKID', geo_id + "." + str(total_count) + "." + str(line_count))
              # print ('    We have the source street line {} len: {}'.format(street_line, street_line.Length()))
              process_line = True
        else:
            if not IsDangle(street_line, 0.0000005):
                # print('    We have the centroid connector {} that is NOT a dangle; connector count: {}, Len {}:  {}'.format(connector_geoIDs_list,
                #                                                                          str(connector_count),
                #                                                                              street_line.Length(),
                #                                                                                           street_line))
                # We have a rare case that the connector overlap (dangle) ran directly over the
                # street segment, meaning the two were in the same direction
                # We don't want to set the geoid for non-connector segments
                # new_feature.SetField('GeoID', geo_id)
                new_feature.SetField('TRACKID', geo_id + "." + str(total_count) + "." + str(line_count))
                connector_count += 1
                process_line = True
            # else:
            #     print ('    We have the centroid connector {} that is a dangle {}, Len {}: {}'.format(connector_geoIDs_list, IsDangle(street_line, 0.000001),
            #                                                                                  street_line.Length(),
            #                                                                                            street_line))
        if (process_line):
            new_feature.SetGeometry(street_line)
            merged_layer.CreateFeature(new_feature)

        line_count += 1

def DeleteFeature(merged_layer, track_id):
  merged_layer.SetAttributeFilter("TRACKID='" + track_id + "'")
  street_feature_delete = merged_layer.GetNextFeature()
  merged_layer.DeleteFeature(street_feature_delete.GetFID())
  merged_layer.SetAttributeFilter(None)

def CreateMergedLayer(merged_layer_file_name):

  '''
  Initializes an ESRI Shapefile with the fields of two
  layers that will be merged - could be improved by creating
  a set of fields from both (assuming they have the same
  definition if sharing names), but just made purpose-built
  for this function - if i have to do again, i'll refactor

  Parameters
  ----------
  merged_layer_file_name : string
    The full path and file name of the new merged layer

  Returns
  -------
    The pointer to the layer
  '''
  print ('About to create shapefile for {}'.format(merged_layer_file_name))

  driver = ogr.GetDriverByName('ESRI Shapefile')
  data_source = driver.CreateDataSource(merged_layer_file_name)

  # create the spatial reference, WGS84
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  new_layer = data_source.CreateLayer(merged_layer_file_name, srs, ogr.wkbLineString)

  new_field = ogr.FieldDefn('GeoID', ogr.OFTString)
  new_field.SetWidth(16)
  new_layer.CreateField(new_field)

  new_field = ogr.FieldDefn('FULLNAME', ogr.OFTString)
  new_field.SetWidth(100)
  new_layer.CreateField(new_field)
  new_field = ogr.FieldDefn('LINEARID', ogr.OFTString)
  new_field.SetWidth(22)
  new_layer.CreateField(new_field)
  new_field = ogr.FieldDefn('MTFCC', ogr.OFTString)
  new_field.SetWidth(5)
  new_layer.CreateField(new_field)
  new_field = ogr.FieldDefn('RTTYP', ogr.OFTString)
  new_field.SetWidth(1)
  new_layer.CreateField(new_field)

  return new_layer

def PrintFeatureFields (layer, feature):
    layerDefinition = layer.GetLayerDefn()
    for i in range(layerDefinition.GetFieldCount()):
        fieldName = layerDefinition.GetFieldDefn(i).GetName()
        print('   Feature field {} has value {}'.format(fieldName, feature.GetField(fieldName)))

def PrintFields(layer):
  layerDefinition = layer.GetLayerDefn()

  for i in range(layerDefinition.GetFieldCount()):
    fieldName = layerDefinition.GetFieldDefn(i).GetName()
    fieldTypeCode = layerDefinition.GetFieldDefn(i).GetType()
    fieldType = layerDefinition.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
    fieldWidth = layerDefinition.GetFieldDefn(i).GetWidth()
    GetPrecision = layerDefinition.GetFieldDefn(i).GetPrecision()

    print ('Name: {} is of Type {}, Width {} and Precision {}'.format(fieldName, fieldType, str(fieldWidth), str(GetPrecision)))

# Create a query using an IN statement to query for the list
# of LINEARID values.
def GetLinearIDInclusionList(linear_id_list):

    exclusion_list = ''.join('\'' + str(id) +'\',' for id in linear_id_list)
    return 'LINEARID IN (' + exclusion_list[:-1] + ')'

# Create a Python list of LINEARID values from the Los Angeles Clipped roads
# that are not in the supplied linear_id_list list
def GetInvertedIDList(linear_id_list, config):

    inverted_id_list = []
    street_layer_src = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['LA_Street_Centerlines'] + '.shp'
    # This is for all of LA
    # street_layer_src = '/Users/cthomas/Development/Data/spatial/Network/streets/tl_2016_06000_roads_la_clipped.shp'
    # This just for RAND
    census_street_network = ogr.Open(street_layer_src)
    census_street_layer = census_street_network.GetLayer(0)
    for census_street_feature in census_street_layer:
        linear_id = census_street_feature.GetField('LINEARID')
        if (linear_id not in linear_id_list):
            inverted_id_list.append(linear_id)

    return inverted_id_list

def GetLineString(linestring_geometry):
  return loads(linestring_geometry.ExportToWkt())

def GetMatchingStreet(census_street_layer, connector_geometry):
  """Given a point, find the line that is closest to that point"""

  has_more_features = True

  connector_point = Point(connector_geometry.GetPoint(1)[0],connector_geometry.GetPoint(1)[1])

  line_feature = census_street_layer.GetNextFeature()
  while has_more_features:
    line_string = GetLineString(ConvertMultilinestringtoLinestring(line_feature.GetGeometryRef()))
    # print("    Point Distance to line {}".format(connector_point.distance(line_string)))
    if (connector_point.distance(line_string) >= 0.00000049 and connector_point.distance(line_string) <= 0.00000051):
      return line_feature
    line_feature = census_street_layer.GetNextFeature()
    # print("Type {}".format(type(line_feature)))
    if (type(line_feature) != "None"):
      has_more_features = False

  return None

def GetUsedIDList(config):
  linear_id_list = []
  connector_layer_src = ogr.Open(config['SPATIAL']['BASE_STREET_PATH'] +
           config['SPATIAL']['LA_Street_Centerlines_Extended'] + '.shp')
  connector_layer = connector_layer_src.GetLayer(0)
  for connector_feature in connector_layer:
    linear_id = connector_feature.GetField('LINEARID')
    if (linear_id not in linear_id_list):
      linear_id_list.append(linear_id)

  return linear_id_list

def write_network_to_disk (config, driver, srs, src_layer):

  new_source = driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                  config['SPATIAL']['LA_Street_Centerlines_Extended'] + '.shp')
  connector_and_streets_intersected_layer_shape = new_source.CreateLayer(
    config['SPATIAL']['LA_Street_Centerlines_Extended'],
    srs, ogr.wkbLineString)

  inLayerDefn = src_layer.GetLayerDefn()
  for i in range(0, inLayerDefn.GetFieldCount()):
    fieldDefn = inLayerDefn.GetFieldDefn(i)
    connector_and_streets_intersected_layer_shape.CreateField(fieldDefn)

  # Get the output Layer's Feature Definition
  connector_layer_rDefn = connector_and_streets_intersected_layer_shape.GetLayerDefn()

  for feature in src_layer:
    out_feat = ogr.Feature(connector_layer_rDefn)

    # Add field values from input Layer
    for i in range(0, connector_layer_rDefn.GetFieldCount()):
      fieldDefn = connector_layer_rDefn.GetFieldDefn(i)
      out_feat.SetField(connector_layer_rDefn.GetFieldDefn(i).GetNameRef(),
                          feature.GetField(i))

    out_feat.SetGeometry(feature.GetGeometryRef().Clone())
    connector_and_streets_intersected_layer_shape.CreateFeature(out_feat)
    out_feat = None
    # connector_and_streets_intersected_layer_shape.SyncToDisk()

  connector_and_streets_intersected_layer_shape  = None
  connector_and_streets_intersected_shape = None

def UnionBlockCentroidStreetLines(execute_level, reentry, config):
  """
  Merge the LA County street lines with the block centroid connector lines
  to create a single dataset of all street segments and connector approximations
  to be used in block-level network routing.  The method makes multiple attempts at
  making sure there is an intersection of the connectors and the street segments.

  Often when a street segment ends near the centroid extender, then it won't
  intersect, so then we have to extend the street segment as well (as the
  centroid extender).

  :param execute_level:  Whether to both create the shape and run the union or just run the union
  :param config: The configuration parser
  :return: None
  """

  ogr.UseExceptions()

  street_layer_src =  config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['LA_Street_Centerlines'] + '.shp'
  connector_layer_src = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['Block_Centroid_Connectors'] + '.csv'
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  shape_driver = ogr.GetDriverByName('ESRI Shapefile')
  """First, create the connector_network_layer from the CSV file created 
      by the connect_block_centroids_to_neares_streets_extend.py script.
      This only needs to be run once per iteration - if built and testing
      the unioning, then this is not needed and should be using execute_level 2"""
  if (execute_level == '1' or execute_level == '4'):
    print('Creating connectors from CSV')
    CreateShapeFromCSV(connector_layer_src)

  """Here we are going to combine the Street Centerlines with the block centroid connectors
     using a variety of means.  The new file will have the fields from the """
  if (execute_level == '2' or execute_level == '4'):
    census_street_network = ogr.Open(street_layer_src)
    census_street_layer = census_street_network.GetLayer(0)

    connector_network = ogr.Open(connector_layer_src.replace('.csv', '.shp'))
    connector_layer = connector_network.GetLayer(0)

    cbc = CensusBlockCentroids()

    memory_driver = ogr.GetDriverByName('MEMORY')
    memory_source = memory_driver.CreateDataSource(config['SPATIAL']['LA_Street_Centerlines_Extended'])

    # shp 8.8 MB, dbf 7.1 MB
    if reentry == 'yes':
      print("Re-entering processing - loading into memory")
      connector_and_streets_intersected_shape = ogr.Open(config['SPATIAL']['BASE_STREET_PATH'] +
                  config['SPATIAL']['LA_Street_Centerlines_Extended'] + '.shp')
      connector_and_streets_intersected_layer_shape = connector_and_streets_intersected_shape.GetLayer(0)

      memory_source.CopyLayer(connector_and_streets_intersected_layer_shape,
                              config['SPATIAL']['LA_Street_Centerlines_Extended'], ['OVERWRITE=YES'])

      connector_and_streets_intersected_layer = memory_source.GetLayer(config['SPATIAL']['LA_Street_Centerlines_Extended'])
    else:


      connector_and_streets_intersected_layer = memory_source.CreateLayer(config['SPATIAL']['LA_Street_Centerlines_Extended'],
                                           srs, ogr.wkbLineString)

      # Create the field definitions
      new_field = ogr.FieldDefn('GeoID', ogr.OFTString)
      new_field.SetWidth(16)
      connector_and_streets_intersected_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('FULLNAME', ogr.OFTString)
      new_field.SetWidth(100)
      connector_and_streets_intersected_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('LINEARID', ogr.OFTString)
      new_field.SetWidth(22)
      connector_and_streets_intersected_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('MTFCC', ogr.OFTString)
      new_field.SetWidth(5)
      connector_and_streets_intersected_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('RTTYP', ogr.OFTString)
      new_field.SetWidth(1)
      connector_and_streets_intersected_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('TRACKID', ogr.OFTString)
      new_field.SetWidth(40)
      connector_and_streets_intersected_layer.CreateField(new_field)


    connector_and_streets_intersected_layer_defn = connector_and_streets_intersected_layer.GetLayerDefn()

    total_count = 0
    lines_processed = 0

    linearidlist = []
    odb = OriginDestinationDB()

    home_geoids_in_los_angeles = 0
    home_geoids_out_los_angeles = 0

    # If we are reentering, then we'll seed the processed list
    if (reentry == 'yes'):
      print("Re-entering processing - identifying previously processed records")
      for processed_feature in connector_and_streets_intersected_layer:
        linearidlist.append(processed_feature.GetField('LINEARID'))

    # if we wanted to do only a subset of the origins, we'd use this and we'd replace the
    # following references to homegeoid to homegeoid[0] - need to clean that up
    # for homegeoid in odb.GetOriginGeoIds('060377019023015'):
    # to do all block centroids, we do the following
    for homegeoid in cbc.GetBlockGeoIDs():

      print ("Home GeoID {}".format(homegeoid))
      connector_layer.SetAttributeFilter("GeoID='" + homegeoid + "'")
      if connector_layer.GetFeatureCount() > 0:
        home_geoids_in_los_angeles += 1
        connector_feature = connector_layer.GetNextFeature()
        connector_geom = connector_feature.GetGeometryRef()
        geom_id = connector_feature.GetField('GeoID')
        # print('Working on Connector [{}]: {}'.format(str(total_count), geom_id))
        total_count += 1
        # Buffer by ~0.1 meter or 0.0000001 decimal degrees in LA.
        connector_end_point = ogr.Geometry(ogr.wkbPoint)
        connector_end_point.AddPoint(connector_geom.GetPoint(1)[0],connector_geom.GetPoint(1)[1])
        bounding_box = connector_end_point.Buffer(0.000001)
        census_street_layer.SetSpatialFilter(bounding_box)
        street_count = 0
        if (census_street_layer.GetFeatureCount() > 0):
            continue_processing = False
            track_id = ''
            street_feature = census_street_layer.GetNextFeature()
            found_intersection = False
            while (not found_intersection) and (street_count < census_street_layer.GetFeatureCount()):
              street_geom = street_feature.GetGeometryRef()
              if (street_geom.Intersects(connector_geom)):
                found_intersection = True
              else:
                street_feature = census_street_layer.GetNextFeature()
                street_count += 1

            if (found_intersection):
              linearid = street_feature.GetField('LINEARID')
              continue_processing = True

              if (linearid not in linearidlist):
                  linearidlist.append(linearid)
              else:
                  # print ("      !! We are pulling from an already processed street {}".format(linearid))
                  # connector_and_streets_intersected_layer.SetAttributeFilter("LINEARID='" + linearid + "'")
                  connector_and_streets_intersected_layer.SetSpatialFilter(bounding_box)
                  # print ("      !! This spatial filter resulted in {} selected streets".format(connector_and_streets_intersected_layer.GetFeatureCount()))
                  street_feature = GetMatchingStreet(connector_and_streets_intersected_layer, connector_geom)
                  if (street_feature is not None):
                    street_geom = street_feature.GetGeometryRef()
                    try:
                      track_id = street_feature.GetField("TRACKID")
                    except:
                      print("    ----- For some reason {} has no feature to act on with count {}".format(linearid,
                                                                                                       census_street_layer.GetFeatureCount()))

              if (street_feature is not None):
                #print ("    Working on Street {} with a connector feature Count {}".format(
                #    street_feature.GetField('LINEARID'), census_street_layer.GetFeatureCount()))

                street_geom = ConvertMultilinestringtoLinestring(street_geom)

                if (street_geom.Intersects(connector_geom)):
                    street_geom = street_geom.Union(connector_geom)
                else:
                    print('    Did not intersect, we are going to try extending street {}'.format(linearid))
                    street_geom_tmp = ExtendStreetStreetSegment(street_geom, connector_geom)
                    if street_geom_tmp != None:
                        if (street_geom_tmp.Intersects(connector_geom)):
                            street_geom = street_geom_tmp.Union(connector_geom)
                        else:
                            print('    >> We are giving up on intersecting this connector!!')
                            continue_processing = False

                if continue_processing:
                    CreateFeatures(street_feature, connector_and_streets_intersected_layer, connector_and_streets_intersected_layer_defn, geom_id,
                                   street_geom, total_count)

                    # Now delete the original feature that got unioned with the connector
                    if (len(track_id) > 0):
                      # print ("About to delete track id {}".format(track_id))
                      DeleteFeature(connector_and_streets_intersected_layer, track_id)
                    #     break
        else:
            # The connector did not intersect with any streets (unlikely but possible)
            CopyFeature(street_feature, connector_and_streets_intersected_layer, connector_and_streets_intersected_layer_defn)
      else:
        home_geoids_out_los_angeles += 1

      if (total_count % 100 == 0):
        print('We have processed {} segments'.format(str(total_count)))


      if (total_count % 20000 == 0):
        print('** Committing to disk {} with features {}'.format(str(total_count),
                                        str(connector_and_streets_intersected_layer.GetFeatureCount())))
        connector_and_streets_intersected_layer.SetSpatialFilter(None)
        write_network_to_disk(config, shape_driver, srs, connector_and_streets_intersected_layer)

    connector_and_streets_intersected_layer.SetSpatialFilter(None)
    write_network_to_disk(config, shape_driver, srs, connector_and_streets_intersected_layer)

    census_street_layer.SetSpatialFilter(None)
    connector_and_streets_intersected_layer = None

    print("We found {} homes in LA and {} ourside of LA".format(home_geoids_in_los_angeles, home_geoids_out_los_angeles))

  if (execute_level == '3' or execute_level == '4'):
    """Now we add the missing street segments (those that did not intersect with any connectors)
       We have to do this in small increments as the full list will break - got a memory
       exception from OSGEO when i tried an attribute filter with more than 10000 entries
       First we invert the list of LINEARIDs from those we've finished to all
       the IDs in the street layer"""
    print ('Calculating inverted ID List')
    linearidlist = []

    if (execute_level == '3'):
      linearidlist = GetUsedIDList(config)

    inverted_linearidlist = GetInvertedIDList(linearidlist, config)
    census_street_network = ogr.Open(street_layer_src)
    census_street_layer = census_street_network.GetLayer(0)
    connector_and_streets_intersected_network = ogr.Open(config['SPATIAL']['BASE_STREET_PATH'] +
                  config['SPATIAL']['LA_Street_Centerlines_Extended'] + '.shp', 1)
    connector_and_streets_intersected_layer = connector_and_streets_intersected_network.GetLayer(0)
    connector_and_streets_intersected_layer_defn = connector_and_streets_intersected_layer.GetLayerDefn()

    print("Our inverted list has {} entries vs those from connector list {}".format(
      len(inverted_linearidlist), len(linearidlist)))

    total_set_count = 0
    # then we'll run batches of queries from this list of the street layer to add back to the merged layer
    continue_processing = True
    print ('Processing batches of the street segments')
    while (continue_processing):
        total_set_count += 1
        inverted_linearid_sublist = []
        for x in range(100):
            if (len(inverted_linearidlist) > 0):
                inverted_linearid_sublist.append(inverted_linearidlist.pop())
            else:
                continue_processing = False
                break

        attribute_filter = GetLinearIDInclusionList(inverted_linearid_sublist)

        # print('Inclusion filter = {}'.format(attribute_filter))
        census_street_layer.SetAttributeFilter(attribute_filter)
        if (census_street_layer.GetFeatureCount() > 0):
            print('We have {} features'.format(census_street_layer.GetFeatureCount()))
            for census_street_feature in census_street_layer:
                CopyFeature(census_street_feature, connector_and_streets_intersected_layer, connector_and_streets_intersected_layer_defn)

        if (total_set_count % 10 == 0):
            print('We have processed {} remaining street segments'.format(str(total_set_count)))

    print ('We\'re about to commit layer!')

    if (execute_level == '5'):
      """Now we'll union the two sets, street segments and census connectors
         First reestablish layer connection after last round of edits"""

      full_merged_ds = shape_driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                                              config['SPATIAL']['LA_Street_Centerlines_Merged'] + '.shp')
      full_merged_layer = full_merged_ds.CreateLayer(
                                              config['SPATIAL']['LA_Street_Centerlines_Merged'],
                                              srs, ogr.wkbLineString)
      # Create the field definitions
      new_field = ogr.FieldDefn('GeoID', ogr.OFTString)
      new_field.SetWidth(16)
      full_merged_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('FULLNAME', ogr.OFTString)
      new_field.SetWidth(100)
      full_merged_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('LINEARID', ogr.OFTString)
      new_field.SetWidth(22)
      full_merged_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('MTFCC', ogr.OFTString)
      new_field.SetWidth(5)
      full_merged_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('RTTYP', ogr.OFTString)
      new_field.SetWidth(1)
      full_merged_layer.CreateField(new_field)
      new_field = ogr.FieldDefn('TRACKID', ogr.OFTString)
      new_field.SetWidth(40)
      full_merged_layer.CreateField(new_field)

      full_merged_layer_defn = full_merged_layer.GetLayerDefn()

      extended_ds = ogr.Open(config['SPATIAL']['BASE_STREET_PATH'] +
                             config['SPATIAL']['LA_Street_Centerlines_Extended'] + '.shp')
      connector_and_streets_intersected_layer = extended_ds.GetLayer(0)

      # Adding the connector segments
      for extended_feature in connector_and_streets_intersected_layer:
          out_feat = ogr.Feature(full_merged_layer_defn)
          out_feat.SetGeometry(extended_feature.GetGeometryRef().Clone())
          SetCensusRoadProperties(extended_feature, out_feat)
          # PrintFeatureFields(connector_and_streets_intersected_layer, out_feat)

          full_merged_layer.CreateFeature(out_feat)
          out_feat = None
          full_merged_layer.SyncToDisk()

      connector_network = ogr.Open(connector_layer_src.replace('.csv', '.shp'))
      connector_layer = connector_network.GetLayer(0)
      for connector_feature in connector_layer:
          out_feat = ogr.Feature(full_merged_layer_defn)
          out_feat.SetGeometry(connector_feature.GetGeometryRef().Clone())
          out_feat.SetField('GeoID', connector_feature.GetField('GeoID'))
          full_merged_layer.CreateFeature(out_feat)
          out_feat = None
          full_merged_layer.SyncToDisk()

      full_merged_layer = None

  census_layer = None
  connector_layer = None
  full_merged_layer = None
  census_street_layer = None
  merged_layer = None
  connector_and_streets_intersected_layer = None
  data_source = None

def main(argv):

  if (len(sys.argv) != 3):

    print ('You must provide the run level and whether this is reentrant.\n' +
           'Valid integer values include\n' +
           '  1: run just the block centroid connector CSV to Shape (only once per full processing round)\n' +
           '  2: intersect the centroid connectors with their nearest streets\n' +
           '  3: merge the insersected centroid/streets with the remaining LA streets\n' +
           '  4: run both 1, 2 and 3')

  else:

    config = configparser.ConfigParser()
    config.read(os.getcwd() + '/params.ini')

    UnionBlockCentroidStreetLines (sys.argv[1], sys.argv[2], config)

if __name__ == '__main__':
  main(sys.argv[1:])