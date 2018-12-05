import osmnx as ox
import configparser, os, sys
import matplotlib
from osgeo import ogr, osr

def import_and_prep_data(config):

  driver = ogr.GetDriverByName('ESRI Shapefile')
  srs = osr.SpatialReference()
  srs.ImportFromEPSG(4326)

  # Grab street centerline from OSM and then we'll clip them at the ~20 mile LA County buffer
  # Tried of all of California but Docker kept killing the process - could have set oom-kill-false
  # But after downloading 200 MB of data, ran into 8 GB memory ceiling - moved to graph_from_bbox
  # california_streets = ox.graph_from_place('California, USA', network_type='drive')
  california_streets = ox.graph_from_bbox(35.114, 33.514, -117.439, -119.316, network_type='drive', simplify=False,
                                          timeout=3600)
  G_projected = ox.project_graph(california_streets)

  print("Created street graph, moving on to saving to disk at {}".format(config['SPATIAL']['BASE_STREET_PATH']))

  ox.save_graph_shapefile(G_projected, filename=config['SPATIAL']['CA_Street_Centerlines_OSM'],
                        folder=config['SPATIAL']['BASE_STREET_PATH'])

  print("Saved street to disk, moving on to clipping")
  la_clip_path = config['DEFAULT']['BASE_PATH_SPATIAL'] + config['SPATIAL']['LA_County_Buffered'] + 'shp'
  la_clip_path_src = ogr.Open(la_clip_path, 0)
  la_clip_layer = la_clip_path_src.GetLayer(0)

  la_california_streets = config['SPATIAL']['BASE_STREET_PATH'] + config['SPATIAL']['CA_Street_Centerlines_OSM'] + 'shp'
  la_california_streets_src = ogr.Open(la_california_streets, 0)
  la_california_streets_layer = la_california_streets_src.GetLayer(0)


  # create the clipped layer from scratch
  la_osm_clipped_streets_src = driver.CreateDataSource(config['SPATIAL']['BASE_STREET_PATH'] +
                                        config['SPATIAL']['LA_Street_Centerlines_OSM'] + '.shp')
  la_osm_clipped_streets_layer = la_osm_clipped_streets_src.CreateLayer(config['SPATIAL']['LA_Street_Centerlines_OSM'],
                                                                    srs, ogr.wkbLineString)

  la_california_streets_layer.clip(la_clip_layer, la_osm_clipped_streets_layer)

def main(argv):

  matplotlib.use('Agg')
  config = configparser.ConfigParser()
  config.read(os.getcwd() + '/params.ini')

  import_and_prep_data(config)

if __name__ == '__main__':
    main(sys.argv[1:])