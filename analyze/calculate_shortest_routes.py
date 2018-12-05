import networkx as nx
import configparser, os, sys
from osgeo import ogr
from census.origin_destination_db import OriginDestinationDB

def ProcessBlockCommutes(config):
  w_geoid = '060377019023041'      #For a block right next to ultimate work geo ID 
  #w_geoid = '060372760005004'     # A block very close to home block - for testing
  r_geoid = '060377019023015'

  dg = nx.read_shp('/ds/data/spatial/Network/streets/tl_2016_06000_roads_la_clipped_extended_split.shp')

  gr = dg.to_undirected()

  dg = None

  centroids_data = ogr.Open('/ds/data/spatial/Census/tl_2016_06_tabblock10_centroids.shp', 0)
  centroids_layer = centroids_data.GetLayer()

  #  identify the key for the target node
  centroids_layer.SetAttributeFilter("GEOID = '{w}'".format(w=w_geoid))
  w_feature = centroids_layer.GetNextFeature()
  w_geometry = w_feature.GetGeometryRef()
  target_network_key = (w_geometry.GetX(), w_geometry.GetY())

  odb = OriginDestinationDB()
  odb.TruncateBlockCommute()

  for h_geoid in odb.GetOriginGeoIds(r_geoid):

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

def main(argv):

  print("starting in main")
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  ProcessBlockCommutes(config)

if __name__ == '__main__':
    main(sys.argv[1:])
