from .streets import Streets
# http://epydoc.sourceforge.net/manual-fields.html
# https://graph-tool.skewed.de/performance
"""Network analysis implementation for the commute justice analysis

   Given a street network, provides methods that wrap some of the 
   complexity of initiating a network graph from a shapefile, offers
   several implementations of Djykstra's shortest path and 
   provides summary information on the network analysis
"""

__author__ = "Cord Thomas"
__license__ = "MIT"
__version__ = "0.1.0"
__maintainer__ = "Cord Thomas"
__email__ = "cord.thomas@gmail.com"
__status__ = "Prototype"

class Network (Streets):
  print("Hello world!!")