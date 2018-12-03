import networkx as nx
from osgeo import ogr

# w_geoid = '060377019023041'   # For a block right next to ultimate work geo ID 
w_geoid = '060372760005004'     # A block very close to home block - for testing
h_geoid = '060372760005002'

 dg = nx.read_shp('/ds/data/spatial/Network/streets/tl_2016_06000_roads_la_clipped_extended_split.shp')

centroids_data = ogr.Open('/ds/data/spatial/Census/tl_2016_06_tabblock10_centroids.shp', 0)
centroids_layer = centroids_data.GetLayer()

# identify the key for the start node
centroids_layer.SetAttributeFilter("GEOID = '{h}'".format(h=h_geoid))
h_feature = centroids_layer.GetNextFeature()
h_geometry = h_feature.GetGeometryRef()
start_network_key = (h_geometry.GetX(), h_geometry.GetY())

start_node = dg[start_network_key] # produces a node object with reasonable values
 
# identify the key for the target node
centroids_layer.SetAttributeFilter("GEOID = '{w}'".format(w=w_geoid))
w_feature = centroids_layer.GetNextFeature()
w_geometry = w_feature.GetGeometryRef()
target_network_key = (w_geometry.GetX(), w_geometry.GetY())

target_node = dg[target_network_key] # produces a node object with reasonable values

path = nx.dijkstra_path(dg, start_network_key, target_network_key, 'weight_dis')
