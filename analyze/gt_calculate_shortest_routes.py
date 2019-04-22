import configparser, os, sys
from osgeo import ogr
import time
from math import isinf
from census.origin_destination_db import OriginDestinationDB
from graph_tool import util as gutil
from graph_tool import topology as gtopo
from graph_tool.all import *

def IsHomeCommuteBlock(odb, block_geoid):

  destinations = odb.GetDestinations(block_geoid)
  return (len(destinations) > 0)

def ProcessAllCommutes(config):

  odb = OriginDestinationDB()
  # odb.TruncateBlockCommute()

  print("Loading directed graph")
  dg = load_graph(config['SPATIAL']['BASE_STREET_PATH'] +
                   config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'] + '.gt')

  vertex_index_field = dg.vertex_properties["latlon"]

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

    if home_geoid == '060374010013001':
      pickup_where_we_left_off = True

    if (pickup_where_we_left_off and IsHomeCommuteBlock(odb, home_geoid)):
      print("Processing Home {}".format(home_geoid))
      t0 = time.time()
      ProcessBlockCommutesFromH(dg, vertex_index_field, home_geoid)
      t1 = time.time()
      total = t1 - t0
      print("    Processed {h} in {t}".format(h=home_geoid, t=total))

def ProcessBlockCommutesFromH(dg, vertex_index_field, h_geoid):
  """Given a Home Census Block, identify all the destination blocks
  and calcluate their commute distances"""

  # h_geoid = '060372760001009'     # Home GeoID
  continue_processing = True

  # identify the key for the home node and then grab the
  # network vertex for that home node.  Keys are of the format
  # latitude:longitude
  odb = OriginDestinationDB()
  result, h_key = odb.GetGTEdgeKey(h_geoid)
  result, additional_commute_distance = odb.GetAdditionalCommuteLengths(h_geoid)
  vertices = gutil.find_vertex(dg, vertex_index_field, h_key)
  if (len(vertices) == 1):
    h_vertex = vertices[0]
    print("    We found the network key for home {} with in degree {}".format(h_key, h_vertex.in_degree()))
  else:
    print("    Could not find home vertex {} for home {}".format(len(vertices), h_key))
    continue_processing = False

  weight_map = dg.edge_properties["weight_dist"]
  # for e in dg.edges():
  #   print("vertex weight: {}".format(weight_map[e]))

  if (continue_processing):
    for w_geoid in odb.GetDestinationGeoIds(h_geoid):
      result, w_key = odb.GetGTEdgeKey(w_geoid[0])
      if (result == 0):
        vertices = gutil.find_vertex(dg, vertex_index_field, w_key)
        if (len(vertices) == 1):
          w_vertex = vertices[0]
          shortest_distance = gtopo.shortest_distance(dg, h_vertex, w_vertex,
                                                      weight_map, directed = False,
                                                      )
          if not isinf(shortest_distance):
            shortest_distance += additional_commute_distance
            odb.InsertBlockCommute(h_geoid, w_geoid[0], shortest_distance)
            print("    We found the network key for work {} with in distance {}".format(w_key, shortest_distance))
          else:
            print("    Could not find the shortest path for {h} to {w}".format(h=h_geoid, w=w_geoid[0]))
        else:
          continue


def ProcessIndividualCommute(config, h_geoid, w_geoid):

  print("Loading directed graph")
  dg = load_graph(config['SPATIAL']['BASE_STREET_PATH'] +
                   config['SPATIAL']['CA_Street_Centerlines_OSM_Clipped'] + '.gt')

  vertex_index_field = dg.vertex_properties["latlon"]

  centroids_data = ogr.Open(config['SPATIAL']['BASE_CENSUS_PATH_SPATIAL'] +
                            config['SPATIAL']['Census_Block10_Centroids'] + '.shp', 0)
  centroids_layer = centroids_data.GetLayer()

  odb = OriginDestinationDB()
  result, h_key = odb.GetGTEdgeKey(h_geoid)

  print("Looking for commute distance from {} to {}".format(h_geoid, w_geoid))
  print("    Home key {}".format(h_key))

  result, additional_commute_distance = odb.GetAdditionalCommuteLengths(h_geoid)
  h_vertices = gutil.find_vertex(dg, vertex_index_field, h_key)
  if (len(h_vertices) == 1):
    h_vertex = h_vertices[0]
    print("    We found the network key for home {} with in degree {}".format(h_key, h_vertex.in_degree()))
  else:
    print("    Could not find home vertex {} for home {}".format(len(h_vertices), h_key))
    continue_processing = False

  weight_map = dg.edge_properties["weight_dist"]
  result, w_key = odb.GetGTEdgeKey(w_geoid)
  if (result == 0):
    w_vertices = gutil.find_vertex(dg, vertex_index_field, w_key)
    print("    Length of work vertices:  {}".format(len(w_vertices)))
    w_vertex = w_vertices[0]
    shortest_distance = gtopo.shortest_distance(dg, h_vertex, w_vertex,
                                                weight_map, directed=False,
                                                )
    if not isinf(shortest_distance):
      shortest_distance += additional_commute_distance
      print("    We found the network key for work {} with in distance {}".format(w_key, shortest_distance))
    else:
      print("    Could not find the shortest path for {h} to {w}".format(h=h_geoid, w=w_geoid))
  else:
    print("     We could not find the work key {}".format(w_geoid))


def print_graph(config):

  print("Loading directed graph")
  dg = load_graph('/ds/data/Project/commute_justice/tl_2016_test.gt')

  vertex_index_field = dg.vertex_properties["latlon"]

  for v in dg.vertices():
    print("Vertex {} has lat-lon of {}".format(v, vertex_index_field[v]))

def main(argv):

  print("starting in main")
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  # print_graph(config)
  # ProcessIndividualCommute(config, '060372760001009', '060377019023015')

  ProcessAllCommutes(config)

if __name__ == '__main__':
    main(sys.argv[1:])
