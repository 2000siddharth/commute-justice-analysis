from preprocess.SplitLinesWithLines import *

# Using testing set
# inputSourceA = '/ds/data/spatial/Network/test/la_streets_with_block_centroid_connectors_test.shp'
# inputSourceB = '/ds/data/spatial/Network/test/la_streets_with_block_centroid_connectors_test.shp'
# outputTarget = '/ds/data/spatial/Network/test/la_streets_with_block_centroid_connectors_test_out.shp'

# For full Los Angeles run
inputSourceA = '/ds/data/spatial/Network/streets/tl_2016_06000_roads_la_clipped_extended.shp'
inputSourceB = '/ds/data/spatial/Network/streets/tl_2016_06000_roads_la_clipped_extended.shp'
outputTarget = '/ds/data/spatial/Network/streets/tl_2016_06000_roads_la_clipped_extended_split.shp'

sl = SplitLinesWithLines()

sl.split_lines_with_lines(inputSourceA, inputSourceB, outputTarget)
