from osgeo import ogr, osr
import sys
from census.origin_destination_db import OriginDestinationDB

ogr.UseExceptions()

censussrc = "/Users/cthomas/Development/Data/spatial/Census/tl_2016_los_angeles_blocks.shp"
targetpath = "/Users/cthomas/Development/Data/spatial/Census/singlesource_2016_06_tabblock10.shp"

# 060377019023015
# Useful notes: https://trac.osgeo.org/gdal/wiki/PythonGotchas
# but still doesn't solve my "python3(94591,0x7fffb524d3c0) malloc: *** error for
#   object 0x10182cd40: pointer being freed was not allocated" problem


# Create a new empty shape layer with a name
# and a type of shape (such as ogr.wkbLineString).
# Defaults to the EPSG 4326, very common coordinates
def CreateNewShapeLayer(shapeName, shapeType):

    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.CreateDataSource(targetpath)

    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    # create the layer
    layer = data_source.CreateLayer(shapeName.rsplit("/", 1)[-1], srs, shapeType)
    new_field = ogr.FieldDefn("GeoID", ogr.OFTString)
    new_field.SetWidth(16)
    layer.CreateField(new_field)

    layer.CreateField(ogr.FieldDefn("RANDCount", ogr.OFTInteger))

    return layer

def GetShapeLayer(layer_name, writable):

    driver = ogr.GetDriverByName("ESRI Shapefile")
    data_source = driver.Open(layer_name, writable)
    shapeLayer = data_source.GetLayer()

    return shapeLayer

def CopyFeature (source_feature, target_layer, target_layerDefn, origin = -1):

    print("Source Feature  ", source_feature.GetField("GEOID10"))
    new_feature = ogr.Feature(target_layerDefn)
    new_feature.SetField("GeoID",  source_feature.GetField("GEOID10"))
    if (origin != -1):
        new_feature.SetField("is_dest", 0)
        new_feature.SetField("s000", origin[1])
        new_feature.SetField("sa01", origin[2])
        new_feature.SetField("sa02", origin[3])
        print ("    Setting sa03 as {}".format(origin[4]))
        new_feature.SetField("sa03", origin[4])
        new_feature.SetField("se01", origin[5])
        new_feature.SetField("se02", origin[6])
        new_feature.SetField("se03", origin[7])
        new_feature.SetField("si01", origin[8])
        new_feature.SetField("si02", origin[9])
        new_feature.SetField("si03", origin[10])
    else:
        new_feature.SetField("is_dest", 1)

    new_feature.SetGeometry(source_feature.GetGeometryRef())
    target_layer.CreateFeature(new_feature)
    new_feature = None

# Use SetAttributeFilter for each h_geoid and make a copy
# of the features.
def ProcessOriginDestinationBlocks(w_geoid):

    odb = OriginDestinationDB()

    print ("Processing origins")

    origins = odb.GetOriginFullData(w_geoid)

    driver = ogr.GetDriverByName("ESRI Shapefile")
    source_data_source = driver.Open(censussrc, 0)
    source_layer = source_data_source.GetLayer()

    data_source = driver.CreateDataSource(targetpath)

    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    # create the layer
    new_layer = data_source.CreateLayer(targetpath.rsplit("/", 1)[-1], srs, ogr.wkbPolygon)
    new_field = ogr.FieldDefn("GeoID", ogr.OFTString)
    new_field.SetWidth(16)
    new_layer.CreateField(new_field)

    new_layer.CreateField(ogr.FieldDefn("is_dest", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("s000", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("sa01", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("sa02", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("sa03", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("se01", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("se02", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("se03", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("si01", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("si02", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("si03", ogr.OFTInteger))

    print ("Source layer of type {} and name {}".format(type(source_layer), source_layer.GetFeatureCount()))
    # print ("Getting RAND Layer Def of type {} with name ".format(type(source_layer), source_layer.GetName()))

    new_layerDefn = new_layer.GetLayerDefn()
    # new_layerDefn = new_layer.GetLayerDefn()

    print ("Ready to Loop It")

    processed_count = 0
    copied_count = 0

    # Copy the destination feature / block (the work block)
    source_layer.SetAttributeFilter("GEOID10 = '{}'".format(w_geoid))
    source_feature = source_layer.GetNextFeature()
    CopyFeature(source_feature, new_layer, new_layerDefn)

    for origin in origins:
        print ("Origin GeoID {}", origin[0])
        source_layer.SetAttributeFilter("GEOID10 = '{}'".format(origin[0]))
        processed_count += 1
        if (source_layer.GetFeatureCount() == 1):
            copied_count += 1
            source_feature = source_layer.GetNextFeature()
            CopyFeature(source_feature, new_layer, new_layerDefn, origin)
        if (processed_count % 100 == 0):
            print ("We've processed {} records".format(processed_count))

    new_layer = None
    data_source = None

    print ("Processed {} and copied {}".format(processed_count, copied_count))

def CreateGeoIDQueryClause (origins):

    clause = ""
    for origin in origins:
        clause = clause + " OR GEOID = '{}'".format(origin[0])

    # if len(clause) > 5:
    #    clause = clause[4:]

    return clause

def ProcessOriginDestinationBlocksWithQuery (w_geoid):
    odb = OriginDestinationDB()

    driver = ogr.GetDriverByName("ESRI Shapefile")
    source_data_source = driver.Open(censussrc, 0)
    # source_layer = source_data_source.GetLayer()

    data_source = driver.CreateDataSource(targetpath)

    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    # create the layer
    new_layer = data_source.CreateLayer(targetpath.rsplit("/", 1)[-1], srs, ogr.wkbPolygon)
    new_field = ogr.FieldDefn("GeoID", ogr.OFTString)
    new_field.SetWidth(16)
    new_layer.CreateField(new_field)

    new_layer.CreateField(ogr.FieldDefn("is_dest", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("s000", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("sa01", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("sa02", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("sa03", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("se01", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("se02", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("se03", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("si01", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("si02", ogr.OFTInteger))
    new_layer.CreateField(ogr.FieldDefn("si03", ogr.OFTInteger))

    new_layerDefn = new_layer.GetLayerDefn()
    # new_layerDefn = new_layer.GetLayerDefn()

    print ("Ready to Loop It")

    processed_count = 0
    copied_count = 0

    # Copy the destination feature / block (the work block)
    #source_layer.SetAttributeFilter("GEOID10 = '{}'".format(w_geoid))
    #source_feature = source_layer.GetNextFeature()
    #CopyFeature(source_feature, new_layer, new_layerDefn)

    origins = odb.GetOriginFullData(w_geoid)
    clause = CreateGeoIDQueryClause(origins)

    home_origin_layer = source_data_source.ExecuteSQL("SELECT * FROM {} WHERE GEOID='{}' {}".format(censussrc.rsplit("/", 1)[-1],
                                                                                               w_geoid, clause))

    for feature in home_origin_layer:
        print (feature)

def main(argv):

  if (len(sys.argv) != 2):

    print ("You must provide the run configuration.\n" +
           "Valid integer values include\n" +
           "  1: run just the block centroid CSV to Shape\n" +
           "  2: run 1 and merge the centroid connectors with the LA streets\n" +
           "  3: run both 1 and 2")

  else:

      ProcessOriginDestinationBlocks (sys.argv[1])

      # ProcessOriginDestinationBlocksWithQuery (sys.argv[1])


if __name__ == "__main__":
  main(sys.argv[1:])