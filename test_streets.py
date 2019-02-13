from osgeo import ogr
from network.streets import Streets
import configparser, os, sys

def test_length(config):
  """Tests the method to find the intersecting point on the nearest street and calculate
  the distance to the nearest end node.  One issue with this is that the commuter may not go
  to the end point, but to the starting point on the edge, but at 50/50 it's hard to say.

  This test was written to support the script identify_nearest_osm_commute_node_to_centroids
  script that populates the nearest_street_node_info database table."""

  la_clipped_streets_osm_src = config['SPATIAL']['BASE_STREET_PATH'] + \
                               config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'] + '.shp'

  la_streets_osm = ogr.Open(la_clipped_streets_osm_src, 0)
  la_streets_osm_layer = la_streets_osm.GetLayer()

  la_streets_osm_layer.SetAttributeFilter("OSMID = '13375447' AND LENGTH = '1044.342'")
  w_seventy_fourth = la_streets_osm_layer.GetNextFeature()

  if (w_seventy_fourth != None):
    streets = Streets.init_with_layer(la_clipped_streets_osm_src)
    test_point = ogr.Geometry(ogr.wkbPoint)
    # test_point.AddPoint(1964269.7970626, 552558.2448765)
    test_point.AddPoint(-118.386628477268, 33.973191755096)
    test_length = streets.GetLengthFromMidpointToEnd(w_seventy_fourth.GetGeometryRef(), test_point)
    print("Test length is {}".format(str(test_length)))

def main(argv):

  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  test_length(config)

if __name__ == '__main__':
    main(sys.argv[1:])
