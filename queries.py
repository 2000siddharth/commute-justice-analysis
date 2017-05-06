from census.census_block import CensusBlock

cb = CensusBlock()

blockPlaceName = cb.getBlockField("block:060372760001009", "stplcname")

print ("Block Place Name {}".format(blockPlaceName))

blockInfo = cb.getBlockInfo("block:060372760001009")

print ("Block Place Name {}".format(blockInfo))

# for the census block data, aland10 = 0 is for waterways, though people seem to commute from waterway blocks...
