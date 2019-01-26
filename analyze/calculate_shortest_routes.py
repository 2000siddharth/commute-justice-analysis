import networkx as nx
import configparser, os, sys
from osgeo import ogr
import time
from census.origin_destination_db import OriginDestinationDB

def ProcessBlockCommutes(config):
  w_geoid = '060377019023015'      #For a block right next to ultimate work geo ID 
  #w_geoid = '060372760005004'     # A block very close to home block - for testing
  r_geoid = '060377019023015'

  h_geoid = '060372760001009'     # Home GeoID
  p_geoid = '060372760001009'     # Proxy for my home GeoID

  print("Loading directed graph")
  dg = nx.read_shp(config['SPATIAL']['BASE_STREET_PATH'] +
                   config['SPATIAL']['LA_Street_Centerlines_Connectors_Split'] + '.shp')

  print("Undirecting graph")
  gr = dg.to_undirected()

  dg = None

  print ("Loading centroid layer {}".format(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp'))

  centroids_data = ogr.Open(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp', 0)
  centroids_layer = centroids_data.GetLayer()

  #  identify the key for the target node
  centroids_layer.SetAttributeFilter("GEOID = '{w}'".format(w=w_geoid))
  w_feature = centroids_layer.GetNextFeature()
  w_geometry = w_feature.GetGeometryRef()
  target_network_key = (w_geometry.GetX(), w_geometry.GetY())

  odb = OriginDestinationDB()
  odb.TruncateBlockCommute()

  for h_geoid in odb.GetOriginGeoIds(w_geoid):

    centroids_layer.SetAttributeFilter("GEOID = '{h}'".format(h=h_geoid[0]))
    # Check to see whether we have this feature; home block could be out of our analysis range
    print ("About to process home {h}".format(h=h_geoid[0]))
    h_feature = centroids_layer.GetNextFeature()
    if (h_feature is not None):
      h_geometry = h_feature.GetGeometryRef()
      source_network_key = (h_geometry.GetX(), h_geometry.GetY())

      if source_network_key in gr and (source_network_key != target_network_key):
        try:
          path_length = nx.dijkstra_path_length(gr, source_network_key, target_network_key, 'weight_dis')
          print("  Commute Distance is {d}".format(d=path_length))

          odb.InsertBlockCommute(h_geoid[0], r_geoid, path_length)
        except nx.exception.NetworkXNoPath as np:
          print("  Exception - No Path")

def IsHomeCommuteBlock(odb, block_geoid):

  destinations = odb.GetDestinations(block_geoid)
  return (len(destinations) > 0)

def ProcessAllCommutes(config):

  odb = OriginDestinationDB()
  # odb.TruncateBlockCommute()

  print("Loading directed graph")
  dg = nx.read_shp(config['SPATIAL']['BASE_STREET_PATH'] +
                   config['SPATIAL']['LA_Street_Centerlines_Connectors_Split'] + '.shp')

  print("Undirecting graph")
  gr = dg.to_undirected()

  dg = None

  print ("Loading centroid layer {}".format(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp'))

  centroids_data = ogr.Open(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp', 0)
  centroids_layer = centroids_data.GetLayer()

  print ("Building list of all block IDs")
  geo_list = []
  for feature in centroids_layer:
    home_geoid = feature.GetField("GeoID")
    geo_list.append(home_geoid)

  print ("Ready to start processing distances")
  pickup_where_we_left_off = False
  for home_geoid in geo_list:
    if not pickup_where_we_left_off:
      print ("Investigating Home {}".format(home_geoid))

    if home_geoid == '060591100062001':
      pickup_where_we_left_off = True

    if (pickup_where_we_left_off and IsHomeCommuteBlock(odb, home_geoid)):
      print("Processing Home {}".format(home_geoid))
      t0 = time.time()
      ProcessBlockCommutesFromHome(config, odb, gr, centroids_layer, home_geoid)
      t1 = time.time()
      total = t1 - t0
      print("Processed {h} in {t}".format(h=home_geoid, t=total))

def ProcessBlockCommutesFromHome(config, odb, gr, centroids_layer, home_geoid):

  #  identify the key for the target node
  centroids_layer.SetAttributeFilter("GEOID = '{h}'".format(h=home_geoid))
  h_feature = centroids_layer.GetNextFeature()
  h_geometry = h_feature.GetGeometryRef()
  target_network_key = (h_geometry.GetX(), h_geometry.GetY())

  print("   About to get destinations {}".format(home_geoid))
  for w_geoid in odb.GetDestinationGeoIds(home_geoid):

    print("   About to process work {}".format(w_geoid[0]))
    centroids_layer.SetAttributeFilter("GEOID = '{h}'".format(h=w_geoid[0]))
    # Check to see whether we have this feature; home block could be out of our analysis range
    # print ("About to process work destination {h}".format(h=w_geoid[0]))
    w_feature = centroids_layer.GetNextFeature()
    if (w_feature is not None):
      w_geometry = w_feature.GetGeometryRef()
      source_network_key = (w_geometry.GetX(), w_geometry.GetY())

      if source_network_key in gr and (source_network_key != target_network_key):
        try:
          path_length = nx.dijkstra_path_length(gr, source_network_key, target_network_key, 'weight_dis')
          print("  Commute Distance is {d}".format(d=path_length))

          odb.InsertBlockCommute(home_geoid, w_geoid[0], path_length)
        except nx.exception.NetworkXNoPath as np:
          print("  Exception - No Path")

  centroids_layer.SetAttributeFilter(None)

def ProcessBlockCommutesFromH(config):
  """Given a Home Census Block, identify all the destination blocks
  and calcluate their commute distances"""
  h_geoid = '060372760001009'     # Home GeoID
  p_geoid = '060372760001009'     # Proxy for my home GeoID

  print("Loading directed graph")
  dg = nx.read_shp(config['SPATIAL']['BASE_STREET_PATH'] +
                   config['SPATIAL']['LA_Street_Centerlines_Connectors_Split'] + '.shp')

  print("Undirecting graph")
  gr = dg.to_undirected()

  dg = None

  centroids_data = ogr.Open(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp', 0)
  centroids_layer = centroids_data.GetLayer()

  #  identify the key for the target node
  centroids_layer.SetAttributeFilter("GEOID = '{h}'".format(h=p_geoid))
  h_feature = centroids_layer.GetNextFeature()
  h_geometry = h_feature.GetGeometryRef()
  target_network_key = (h_geometry.GetX(), h_geometry.GetY())

  odb = OriginDestinationDB()

  for w_geoid in odb.GetDestinationGeoIds(p_geoid):

    centroids_layer.SetAttributeFilter("GEOID = '{w}'".format(w=w_geoid[0]))
    # Check to see whether we have this feature; home block could be out of our analysis range
    print ("About to process work {w}".format(w=w_geoid[0]))
    w_feature = centroids_layer.GetNextFeature()
    if (w_feature is not None):
      w_geometry = w_feature.GetGeometryRef()
      source_network_key = (w_geometry.GetX(), w_geometry.GetY())

      if source_network_key in gr and (source_network_key != target_network_key):
        try:
          path_length = nx.dijkstra_path_length(gr, source_network_key, target_network_key, 'weight_dis')
          print("  Commute Distance is {d}".format(d=path_length))

          odb.InsertBlockCommute(h_geoid, w_geoid[0], path_length)
        except nx.exception.NetworkXNoPath as np:
          print("  Exception - No Path")

def main(argv):

  print("starting in main")
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  ProcessAllCommutes(config)

if __name__ == '__main__':
    main(sys.argv[1:])
