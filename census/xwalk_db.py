import sqlite3
from .census_db import *

class XWalkDB(CensusDB):

  # some constants about the database table
  tbl = 'xwalk'

  def GetBlock(self, geoid):

    blockSQL = "SELECT * FROM xwalk WHERE tabblk2010=?"
    result, block = self.select_many(blockSQL, [geoid])
    return block


