from osgeo import ogr
from osgeo import osr
import csv
from math import sqrt
import sys
from shapely.geometry import mapping, shape
from shapely.ops import cascaded_union
from fiona import collection

# Intersect the census provided streets with the census block centroid street connectors
# http://gdal.org/python/osgeo.ogr.Layer-class.html#Union


# From https://pcjericks.github.io/py-gdalogr-cookbook/vector_layers.html#create-a-new-shapefile-and-add-data
# To abstract this to any CSV, would want to:
#   add arguement for coordinate spatial reference
#   read shapetype from first field's WKT value (POINT, LINESTRING) and convert to ogr
#   iterate over fields in CSV to add to fields in Shapefile
def CreateShapeFromCSV(csvFileName):

  print ("Creating shape from CSV {} as {}".format(csvFileName, csvFileName.replace(".csv", ".shp")))
  reader = csv.DictReader(open(csvFileName, "rt"),
                          delimiter='\t',
                          quoting=csv.QUOTE_MINIMAL)

  driver = ogr.GetDriverByName("ESRI Shapefile")
  data_source = driver.CreateDataSource(csvFileName.replace(".csv", ".shp"))

  # create the spatial reference, WGS84
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  # create the layer
  print("About to create layer")
  layer = data_source.CreateLayer("street_connectors", srs, ogr.wkbLineString)

  field_name = ogr.FieldDefn("GeoID", ogr.OFTString)
  field_name.SetWidth(16)
  layer.CreateField(field_name)

  n = 0
  print("About to iterate over CSV")
  for row in reader:
    # create the feature
    feature = ogr.Feature(layer.GetLayerDefn())
    # Set the attributes using the values from the delimited text file
    feature.SetField("GeoID", row['GeoID'].replace("'", ""))

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

  print ("Processed {} segments".format(str(n)))

def CountLayerFeatures(layer):
  featureCount = layer.GetFeatureCount()
  print ("There are {} features in {}".format(str(featureCount), layer.GetName()))

# Convert a multilinestring to a linestring
def ConvertMultilinestringtoLinestring(multilinestring):

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

def SetCensusRoadProperties (source_feature, new_feature):
    new_feature.SetField("FULLNAME", source_feature.GetField("FULLNAME"))
    new_feature.SetField("LINEARID", source_feature.GetField("LINEARID"))
    new_feature.SetField("MTFCC", source_feature.GetField("MTFCC"))
    new_feature.SetField("RTTYP", source_feature.GetField("RTTYP"))


def CopyFeature (source_feature, target_layer, target_layerDefn, origin = -1):

    new_feature = ogr.Feature(target_layerDefn)
    if (source_feature.GetDefnRef().GetFieldIndex("LINEARID") != -1) :
        SetCensusRoadProperties(source_feature, new_feature)
    else:
        new_feature.SetField("GeoID", source_feature.GetField("GeoID"))

    new_feature.SetGeometry(source_feature.GetGeometryRef())
    # PrintFeatureFields(target_layer, new_feature)
    target_layer.CreateFeature(new_feature)
    new_feature = None

def IsDangle (line_geometry, dangle_length):
    return line_geometry.Length() <= dangle_length

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
    """
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
    """

    buffered_connector = conector_segment_geom.Buffer(0.0000001)
    for i in range(0, street_segment_geom.GetPointCount()):
        # print ("  Looking at index {}".format(str(i)))
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(street_segment_geom.GetPoint(i)[0],street_segment_geom.GetPoint(i)[1])
        if point.Within(buffered_connector):
            print("  We found the index {}".format(str(i)))
            return i

    return -1

def ConvertMultiLinetoLineString(street_segment_geom):

    if (street_segment_geom.GetGeometryType() == ogr.wkbLineString):
        return street_segment_geom
    else:
        return ConvertMultilinestringtoLinestring(street_segment_geom)

def ExtendStreetStreetSegment(street_segment_geom, connector_segment_geom):

    # print ("     The street segment {}\n      The connector segment {}".format(street_segment_geom,
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
                                         start_point, end_point, 0.0000005)
        return street_segment_geom

    return None

def CreateFeatures(census_street_feature, merged_layer, merged_layer_defn,
                   geo_id, census_street_geom):
    """
    Creates new features in the merged layer assuming that a Union happened
    and that we have one or more census block connectors split at the street
    lines along with split street lines.  The census_street_geom is going to
    be a MULTILINESTRING (check for that) which will first have a set of
    LINESTRINGs that are the split street lines and then a set of
    LINESTRINGs that are the split block centroid connectors with a dangle

    Parameters
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
    """

    line_count = 1
    connector_count = 0
    total_line_seg_count = LineSegmentCount(census_street_geom)
    new_feature = ogr.Feature(merged_layer_defn)
    for street_line in census_street_geom:
        print ("  Geometry Feature Count {}".format(str(line_count)))
        process_line = False
        if  (line_count <= total_line_seg_count / 2):
            SetCensusRoadProperties(census_street_feature, new_feature)
            # print ("    We have the source street line {} len: {}".format(street_line, street_line.Length()))
            process_line = True
        else:
            if not IsDangle(street_line, 0.000001):
                # print("    We have the centroid connector {} that is NOT a dangle; connector count: {}, Len {}:  {}".format(connector_geoIDs_list,
                #                                                                          str(connector_count),
                #                                                                              street_line.Length(),
                #                                                                                           street_line))
                # We have a rare case that the connector overlap (dangle) ran directly over the
                # street segment, meaning the two were in the same direction
                new_feature.SetField("GeoID", geo_id)
                connector_count += 1
                process_line = True
            # else:
            #     print ("    We have the centroid connector {} that is a dangle {}, Len {}: {}".format(connector_geoIDs_list, IsDangle(street_line, 0.000001),
            #                                                                                  street_line.Length(),
            #                                                                                            street_line))
        if (process_line):
            new_feature.SetGeometry(street_line)
            merged_layer.CreateFeature(new_feature)

        line_count += 1

def CreateMergedLayer(merged_layer_file_name):

  """
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
  """
  print ("About to create shapefile for {}".format(merged_layer_file_name))

  driver = ogr.GetDriverByName("ESRI Shapefile")
  data_source = driver.CreateDataSource(merged_layer_file_name)

  # create the spatial reference, WGS84
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  new_layer = data_source.CreateLayer(merged_layer_file_name, srs, ogr.wkbLineString)

  new_field = ogr.FieldDefn("GeoID", ogr.OFTString)
  new_field.SetWidth(16)
  new_layer.CreateField(new_field)

  new_field = ogr.FieldDefn("FULLNAME", ogr.OFTString)
  new_field.SetWidth(100)
  new_layer.CreateField(new_field)
  new_field = ogr.FieldDefn("LINEARID", ogr.OFTString)
  new_field.SetWidth(22)
  new_layer.CreateField(new_field)
  new_field = ogr.FieldDefn("MTFCC", ogr.OFTString)
  new_field.SetWidth(5)
  new_layer.CreateField(new_field)
  new_field = ogr.FieldDefn("RTTYP", ogr.OFTString)
  new_field.SetWidth(1)
  new_layer.CreateField(new_field)

  return new_layer

def PrintFeatureFields (layer, feature):
    layerDefinition = layer.GetLayerDefn()
    for i in range(layerDefinition.GetFieldCount()):
        fieldName = layerDefinition.GetFieldDefn(i).GetName()
        print("   Feature field {} has value {}".format(fieldName, feature.GetField(fieldName)))

def PrintFields(layer):
  layerDefinition = layer.GetLayerDefn()

  for i in range(layerDefinition.GetFieldCount()):
    fieldName = layerDefinition.GetFieldDefn(i).GetName()
    fieldTypeCode = layerDefinition.GetFieldDefn(i).GetType()
    fieldType = layerDefinition.GetFieldDefn(i).GetFieldTypeName(fieldTypeCode)
    fieldWidth = layerDefinition.GetFieldDefn(i).GetWidth()
    GetPrecision = layerDefinition.GetFieldDefn(i).GetPrecision()

    print ("Name: {} is of Type {}, Width {} and Precision {}".format(fieldName, fieldType, str(fieldWidth), str(GetPrecision)))

def GetLinearIDExclusionList(linear_id_list):

    exclusion_list = ''.join('\'' + str(id) +'\',' for id in linear_id_list)
    return 'LINEARID NOT IN (' + exclusion_list[:-1] + ')'

# Merge the LA County street lines with the block centroid connector lines
# to create a single dataset of all street segments and connector approximations
# to be used in block-level network routing.
def UnionBlockCentroidStreetLines(execute_level):

  ogr.UseExceptions()

  censusstreetlayersrc = "/Users/cthomas/Development/Data/spatial/Network/streets/tl_2016_06000_roads_la_clipped.shp"
  connectorlayersrc = "/Users/cthomas/Development/Data/spatial/Network/streets/street_segment_block_centroid_connectors_extend.csv"

  if (execute_level == '1' or execute_level == '3'):
    print("Creating connectors from CSV")
    CreateShapeFromCSV(connectorlayersrc)

  if (execute_level == '2' or execute_level == '3'):
    census_street_network = ogr.Open(censusstreetlayersrc)
    census_street_layer = census_street_network.GetLayer(0)

    connector_network = ogr.Open(connectorlayersrc.replace(".csv", ".shp"))
    connector_layer = connector_network.GetLayer(0)

    # PrintFields(census_street_layer)


    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(censusstreetlayersrc.rsplit("/", 1)[0] + "/tl_2016_06000_roads_la_clipped_extended.shp")
    extended_layer = data_source.CreateLayer("tl_2016_06000_roads_la_clipped_extended",
                                           srs, ogr.wkbLineString)

    # Create the field definitions
    new_field = ogr.FieldDefn("GeoID", ogr.OFTString)
    new_field.SetWidth(16)
    extended_layer.CreateField(new_field)
    new_field = ogr.FieldDefn("FULLNAME", ogr.OFTString)
    new_field.SetWidth(100)
    extended_layer.CreateField(new_field)
    new_field = ogr.FieldDefn("LINEARID", ogr.OFTString)
    new_field.SetWidth(22)
    extended_layer.CreateField(new_field)
    new_field = ogr.FieldDefn("MTFCC", ogr.OFTString)
    new_field.SetWidth(5)
    extended_layer.CreateField(new_field)
    new_field = ogr.FieldDefn("RTTYP", ogr.OFTString)
    new_field.SetWidth(1)
    extended_layer.CreateField(new_field)

    extended_layer_defn = extended_layer.GetLayerDefn()

    total_count = 0

    # LINEARID 1101583236958  does not intersect
    # with connector GeoID 060378004101007 (LINESTRING (-118.7184635353147 34.03795005627166,-118.71887206743176 34.0349485045679)) though it should

    # This approach uses the connectors as the loop rather than the street segments.  In the end, it then
    # identifies all street segments that did not intersect with connectors and adds those as well.  This is a
    # rather expensive query to execute, but should work
    # connector_layer.SetAttributeFilter("GeoID='060375541051003' OR GeoID='060375531003008' OR GeoID='060375541051004' "
    #                                    "OR GeoID='060375541051002' OR GeoID='060375545213009' OR GeoID='060375545213009'"
    #                                    "OR GeoID='060375531004010' OR GeoID='060375542031006'" )
    # connector_layer.SetAttributeFilter("GeoID='060375541051003' OR GeoID='060375541051002' OR GeoID='060375545213009' OR GeoID='060375545213009'")
    linearidlist = []
    for connector_feature in connector_layer:
        connector_geom = connector_feature.GetGeometryRef()
        geom_id = connector_feature.GetField("GeoID")
        print("Working on Connector {}".format(geom_id))
        total_count += 1
        # Buffer by ~0.1 meter or 0.0000001 decimal degrees in LA.
        bounding_box = connector_geom.Buffer(0.0000001)
        census_street_layer.SetSpatialFilter(bounding_box)
        street_count = 0
        if (census_street_layer.GetFeatureCount() > 0):
            continue_processing = False
            for census_street_feature in census_street_layer:
                linearid = census_street_feature.GetField("LINEARID")
                if (linearid not in linearidlist):
                    linearidlist.append(linearid)
                print("Working on Street {} with a connector feature Count {}".format(
                    census_street_feature.GetField("LINEARID"), census_street_layer.GetFeatureCount()))
                continue_processing = True
                census_street_geom = census_street_feature.GetGeometryRef()
                census_street_geom = ConvertMultilinestringtoLinestring(census_street_geom)
                # Following union should create a MULTILINESTRING with 2 parts from the street network
                # and two parts from the connector.  We then want to drop the dangle
                # if (census_street_geom.Touches(connector_geom)):
                #     print  ("They touched")
                # print("Working on Street {}".format(census_street_geom))
                print("     Geometry is now {}".format(census_street_geom.GetGeometryName()))
                if (census_street_geom.Intersects(connector_geom)):
                    census_street_geom = census_street_geom.Union(connector_geom)
                else:
                    print("    Did not intersect, we are going to try extending street {}".format(
                        census_street_feature.GetField("LINEARID")))
                    census_street_geom_tmp = ExtendStreetStreetSegment(census_street_geom, connector_geom)
                    if census_street_geom_tmp != None:
                        if (census_street_geom_tmp.Intersects(connector_geom)):
                            census_street_geom = census_street_geom_tmp.Union(connector_geom)
                        else:
                            continue_processing = False

            if continue_processing:
                CreateFeatures(census_street_feature, extended_layer, extended_layer_defn, geom_id,
                               census_street_geom)
                #     break
        else:
            # The connector did not intersect with any streets (unlikely but possible)
            CopyFeature(census_street_feature, extended_layer, extended_layer_defn)

        if (total_count % 1000 == 0):
            print("We have processed {} segments".format(str(total_count)))

    # Now we add the missign street segments (those that did not intersect with any connectors)
    attribute_filter = GetLinearIDExclusionList(linearidlist)
    census_street_layer.SetSpatialFilter(None)
    print("Exclusion filter = {}".format(attribute_filter))
    census_street_layer = census_street_network.GetLayer(0)
    if (census_street_layer.GetFeatureCount() > 0):
        print("A = feature count {}".format(census_street_layer.GetFeatureCount()))
    census_street_layer.SetAttributeFilter(attribute_filter)
    if (census_street_layer.GetFeatureCount() > 0):
        print("B = feature count {}".format(census_street_layer.GetFeatureCount()))
    # census_street_layer.ResetReading()
    for census_street_feature in census_street_layer:
        CopyFeature(census_street_feature, extended_layer, extended_layer_defn)


    # LINEARID 1103747746552 does seem to fit in the buffer, but doesn't intersect with anything
    # First sweep we identify the connectors that don't intersect a street segment and we'll rewrite
    # the street segment data to extend those files
    # Then we'll union the connectors to the

    # Here we will look for any and all street segments that are near
    # to census connectors but do not intersect them.  This most often
    # happens at the end node of a street segment that touches a connector
    # but does not technically intersect.  Even the Touches() method fails.
    # census_street_layer.SetAttributeFilter("LINEARID='1101576648263' OR LINEARID='1101576665855' OR LINEARID='1101576666244'"
    #                                        " OR LINEARID='1101576666055'  OR LINEARID='1101576666197'  OR LINEARID='1101576665939'")
    # census_street_layer.SetAttributeFilter("LINEARID='1101576648263' OR LINEARID='1101576665855' "
    #     " OR LINEARID='1101576648546' OR LINEARID='1101576666115' OR LINEARID='1101576666031' ")
    # Here we have 3 possible outcomes in this loop:
    #   1 - the street doesn't intersect with any connectors, we simply make a copy of it
    #   2 - the street intersects with one or more connectors, we
    # for census_street_feature in census_street_layer:
    #   census_street_geom = census_street_feature.GetGeometryRef()
    #   print("Working on Street {}".format(census_street_feature.GetField("LINEARID")))
    #   census_street_geom = ConvertMultilinestringtoLinestring(census_street_geom)
    #   total_count += 1
    #   # Buffer by ~0.1 meter or 0.0000001 decimal degrees in LA.
    #   bounding_box = census_street_geom.Buffer(0.0000001)
    #   connector_layer.SetSpatialFilter (bounding_box)
    #   if (connector_layer.GetFeatureCount() > 0):
    #       for connector_feature in connector_layer:
    #           connector_geom  = connector_feature.GetGeometryRef()
    #           print ("   We are working on Connector {}".format(connector_feature.GetField("GeoID")))
    #           # Following union should create a MULTILINESTRING with 2 parts from the street network
    #           # and two parts from the connector.  We then want to drop the dangle
    #           if (not census_street_geom.Intersects(connector_geom)):
    #               print ("    Did not intersect, we are going to try extending street for connector {}".format(connector_feature.GetField("GeoID")))
    #               census_street_geom_ext = ExtendStreetStreetSegment(census_street_geom, connector_geom)
    #               census_street_feature_new = ogr.Feature(extended_layer_defn)
    #               SetCensusRoadProperties(census_street_feature, census_street_feature_new)
    #               print ("       We got here")
    #               census_street_feature_new.SetGeometry(census_street_geom_ext)
    #               # census_street_geom = census_street_geom_ext
    #               # PrintFeatureFields(census_street_layer, census_street_feature_new)
    #               # print ("    Did not intersect, we have original geom {} \nand new feature {} ".format(census_street_geom,
    #               #                                                                                       census_street_feature_new.GetGeometryRef()))
    #
    #       if (census_street_feature_new != None):
    #           print("    === Copying new features")
    #           CopyFeature(census_street_feature_new, extended_layer, extended_layer_defn)
    #       else:
    #           print("    === Copying orig features")
    #           CopyFeature(census_street_feature, extended_layer, extended_layer_defn)
    #       census_street_feature_new = None
    #   else:
    #     # The street segment intersected with no connectors, just copy it
    #     CopyFeature(census_street_feature, extended_layer, extended_layer_defn)
    #   if (total_count % 1000 == 0):
    #       print("We have processed {} segments".format(str(total_count)))

    print ("We're about to commit layer!")

    if (1 == 2):
        # Now we'll union the two sets, street segments and census connectors
        # First reestablish layer connection after last round of edits
        full_merged_ds = driver.CreateDataSource(censusstreetlayersrc.rsplit("/", 1)[0] + "/tl_2016_06000_roads_la_clipped_merged.shp")
        full_merged_layer = full_merged_ds.CreateLayer("tl_2016_06000_roads_la_clipped_merged", srs, ogr.wkbLineString)
        # Create the field definitions
        new_field = ogr.FieldDefn("GeoID", ogr.OFTString)
        new_field.SetWidth(16)
        full_merged_layer.CreateField(new_field)
        new_field = ogr.FieldDefn("FULLNAME", ogr.OFTString)
        new_field.SetWidth(100)
        full_merged_layer.CreateField(new_field)
        new_field = ogr.FieldDefn("LINEARID", ogr.OFTString)
        new_field.SetWidth(22)
        full_merged_layer.CreateField(new_field)
        new_field = ogr.FieldDefn("MTFCC", ogr.OFTString)
        new_field.SetWidth(5)
        full_merged_layer.CreateField(new_field)
        new_field = ogr.FieldDefn("RTTYP", ogr.OFTString)
        new_field.SetWidth(1)
        full_merged_layer.CreateField(new_field)

        full_merged_layer_defn = full_merged_layer.GetLayerDefn()

        extended_ds = ogr.Open(censusstreetlayersrc.rsplit("/", 1)[0] + "/tl_2016_06000_roads_la_clipped_extended.shp")
        extended_layer = extended_ds.GetLayer()
        for extended_feature in extended_layer:
            out_feat = ogr.Feature(full_merged_layer_defn)
            out_feat.SetGeometry(extended_feature.GetGeometryRef().Clone())
            SetCensusRoadProperties(extended_feature, out_feat)
            PrintFeatureFields(extended_layer, out_feat)

            full_merged_layer.CreateFeature(out_feat)
            out_feat = None
            full_merged_layer.SyncToDisk()

        connector_network = ogr.Open(connectorlayersrc.replace(".csv", ".shp"))
        connector_layer = connector_network.GetLayer(0)
        for connector_feature in connector_layer:
            out_feat = ogr.Feature(full_merged_layer_defn)
            out_feat.SetGeometry(connector_feature.GetGeometryRef().Clone())
            out_feat.SetField("GeoID", connector_feature.GetField("GeoID"))
            full_merged_layer.CreateFeature(out_feat)
            out_feat = None
            full_merged_layer.SyncToDisk()

        full_merged_layer = None

    if (1 == 2):
        # Now we merge - let's see what happens
        with collection(censusstreetlayersrc.rsplit("/", 1)[0] + "/tl_2016_06000_roads_la_clipped_merged.shp", "r") as input:
            schema = input.schema.copy()
            with collection(
                            censusstreetlayersrc.rsplit("/", 1)[0] + "/tl_2016_06000_roads_la_clipped_connectors_merged.shp", "w", "ESRI Shapefile", schema) as output:
                shapes = []
                for f in input:
                    shapes.append(shape(f['geometry']))
                merged = cascaded_union(shapes)
                output.write({
                    'properties': {
                        'name': 'Buffer Area'
                    },
                    'geometry': mapping(merged)
                })

  census_layer = None
  connector_layer = None
  full_merged_layer = None
  census_street_layer = None
  merged_layer = None
  extended_layer = None
  data_source = None

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

    print ("Line 1 and 2 Intersect: {}".format(line1.Intersects(line2)))

def main(argv):

  if (len(sys.argv) != 2):

    print ("You must provide the run configuration.\n" +
           "Valid integer values include\n" +
           "  1: run just the block centroid CSV to Shape\n" +
           "  2: run 1 and merge the centroid connectors with the LA streets\n" +
           "  3: run both 1 and 2")

  else:

    UnionBlockCentroidStreetLines (sys.argv[1])

if __name__ == "__main__":
  main(sys.argv[1:])