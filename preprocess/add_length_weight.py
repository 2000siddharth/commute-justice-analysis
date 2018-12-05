import configparser, os, sys
from osgeo import ogr, osr

def add_weight(src):
  """ Add a weight field to the shapefile based on the length
  :param src:  The absolute path to the Shapefile to convert
  :param with_progress:  Show progress as the number of edges
  processed in the Shapefile conversion to GT network; default
  is false.
  :return:  None
  """
  shape_layer_src = src
  driver = ogr.GetDriverByName('ESRI Shapefile')
  shape_datasource = driver.Open(shape_layer_src, 1)
  shape_layer = shape_datasource.GetLayer(0)
  shape_layer_defn = shape_layer.GetLayerDefn()
  shape_layer.CreateField(ogr.FieldDefn("weight_dis", ogr.OFTReal))

  source = osr.SpatialReference()
  source.ImportFromEPSG(4326)

  target = osr.SpatialReference()
  target.ImportFromEPSG(26945)

  transform = osr.CoordinateTransformation(source, target)

  for feature in shape_layer:
    geom = feature.GetGeometryRef().Clone()
    geom.Transform(transform)
    length = geom.Length()
    feature.SetField("weight_dis", length)
    shape_layer.SetFeature(feature)

  shape_layer = None
  shape_datasource = None

def main(argv):
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')
  add_weight('/Users/cthomas/Development/data/spatial/Network/streets/tl_2016_06000_roads_la_clipped_extended_split.shp')

if __name__ == "__main__":
  main(sys.argv[1:])