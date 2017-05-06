from osgeo import ogr
from osgeo import osr
from osgeo import gdal
import csv
import sys
import time
from census.origin_destination_db import OriginDestinationDB
from census.census_block_centroids_sp import CensusBlockCentroids
from network.streets import Streets

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

def CreateNewShapeLayer(shapeName):
  print ("Creating layer {}".format(shapeName))
  driver = ogr.GetDriverByName("ESRI Shapefile")
  data_source = driver.CreateDataSource(shapeName)

  # create the spatial reference, WGS84
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  # create the layer
  layer = data_source.CreateLayer(shapeName.rsplit("/", 1)[-1], srs, ogr.wkbLineString)
  print ("Created layer {}".format(shapeName))

  return layer

def CountLayerFeatures(layer):
  featureCount = layer.GetFeatureCount()
  print ("There are {} features in {}".format(str(featureCount), layer.GetName()))

def UnionBlockCentroidStreetLines():
  

  censusstreetlayersrc = "/Users/cthomas/Development/Data/spatial/Network/streets/tl_2016_06000_roads_la_clipped.shp"
  censusStreets = ogr.Open(censusstreetlayersrc, 0)
  censuslayer = censusStreets.GetLayer()

  connectorlayersrc = "/Users/cthomas/Development/Data/spatial/Network/streets/street_segment_block_centroid_connectors.csv"
  # CreateShapeFromCSV(connectorlayersrc)

  CountLayerFeatures(censuslayer)

  connectorStreets = ogr.Open(connectorlayersrc.replace(".csv", ".shp"), 0)
  connectorLayer = connectorStreets.GetLayer()

  CountLayerFeatures(connectorLayer)

  outputLayer = CreateNewShapeLayer(censusstreetlayersrc.rsplit("/", 1)[0] + "/la_streets_with_block_centroid_connectors.shp")

  print("About to union the layers")

  censuslayer.Union(connectorLayer, outputLayer)

  print("Unioned Layers")

  CountLayerFeatures(outputLayer)

  outputLayer = None
  censuslayer = None
  connectorLayer = None

UnionBlockCentroidStreetLines()

