import sqlite3

class CensusDB():

  census_sqlite = '/Users/cthomas/Development/Data/Census/census.db'

  def __init__(self):

    self.conn = sqlite3.connect(self.census_sqlite)
    self.cur = self.conn.cursor()

  def commit(self):
    self.conn.commit()

  # Execute a statement not caring about the outcome, such
  # as an insert without caring about a provided autoincremented
  # key or an updated record count
  def exec(self, sql_statement):
    try:
      self.cur.execute(sql_statement)
    except sqlite3.IntegrityError:
      return -1, "Primary Key Violation"
    return 0, "Success"

  # Execute a statement not caring about the outcome, such
  # as an insert without caring about a provided autoincremented
  # key or an updated record count
  def exec(self, sql_statement, params):
    try:
      self.cur.execute(sql_statement, params)
    except sqlite3.IntegrityError:
      return -1, "Primary Key Violation"
    return 0, "Success"

  # Execute a statement not caring about the outcome, such
  # as an insert without caring about a provided autoincremented
  # key or an updated record count
  def insert(self, sql_statement, paramlist):
    try:
      self.cur.execute(sql_statement, paramlist)
    except sqlite3.IntegrityError:
      return -1, "Primary Key Violation"
    return 0, "Success"

  # Select many records 
  # Return a
  def select_many(self, *args):
#    try:
    if len(args) == 1:
      self.cur.execute(args[0])
      all_data = self.cur.fetchall()
      return 0, all_data
    elif len(args) == 2:
      try:
        self.cur.execute(args[0], (args[1],))
        all_data = self.cur.fetchall()
        return 0, all_data
      except NameError:
        print("Name Error")
      except ValueError:
        print("parameters are of unsupported type")
      except IOError:
        print("IO error")
      except:
        return -1, "Error selecting data"

  def select_one(self, sql_statement):
    try:
      self.cur.execute(sql_statement)
      one_data = self.cur.fetchone()
      return 0, one_data
    except:
      return -1, "Error finding record"
