from network.streets import Streets

streets = Streets()

print ("Total road segments {}".format(streets.GetCountAllRoadSegments()))

print("Total road length in California is: {}m".format(streets.GetLengthAllRoads()))

print("Total road length of W 74th Street is: {}m".format(streets.GetLengthRoad("W 74th St")))
