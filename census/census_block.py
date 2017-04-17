import redis
import time

class CensusBlock:

  redIs = redis.Redis()
  blockFields = {"st","stusps","stname","cty","ctyname","trct","trctname","bgrp","bgrpname","cbsa",
    "cbsaname", "zcta","zctaname","stplc","stplcname","ctcsub","ctycsubname","stcd114","stcd114name",
    "stsldl","stsldlname"}

  def getBlockField(self, blockCode, fieldName):
    block = self.redIs.hget(blockCode, fieldName)
    return block  
  
  def getBlockInfo(self, blockCode):
    block = self.redIs.hmget(blockCode, self.blockFields)
    return block


