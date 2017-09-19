from osgeo import ogr
from osgeo import osr
import geopandas as gpd
import pandas as pd
import csv
import sys

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

# Merge the LA County street lines with the block centroid connector lines
# to create a single dataset of all street segments and connector approximations
# to be used in block-level network routing.
def UnionBlockCentroidStreetLines(execute_level):

  ogr.UseExceptions()

  censusstreetlayersrc = "/Users/cthomas/Development/Data/spatial/Network/streets/tl_2016_06000_roads_la_clipped.shp"
  connectorlayersrc = "/Users/cthomas/Development/Data/spatial/Network/streets/street_segment_block_centroid_connectors.csv"
  census_layer = gpd.read_file(censusstreetlayersrc)

  if (execute_level == '1' or execute_level == '3'):
    print("Creating connectors from CSV")
    CreateShapeFromCSV(connectorlayersrc)

  if (execute_level == '2' or execute_level == '3'):
    print("Merging connectors with LA streets")
    connector_layer = gpd.read_file(connectorlayersrc.replace(".csv", ".shp"))
    mergedStreets = pd.concat([census_layer, connector_layer], ignore_index=True)
    # CountLayerFeatures(mergedStreets)
    mergedStreets.to_file(censusstreetlayersrc.rsplit("/", 1)[0] + "/la_streets_with_block_centroid_connectors.shp")

  census_layer = None
  connector_layer = None

def main(argv):

  print ("Length {} of args {}", len(sys.argv), sys.argv[1])

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