import math
import os
import sys
from sys import maxsize

from osgeo import osr
from osgeo import ogr
ogr.UseExceptions()

# From https://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/densify.py
# Densify slices up a line segment into sub sections
# based on a preferred length and options on what
# to do in the event that the line cannot be perfectly
# sliced based on the dimensions.
class Densify(distance, remainder):

    distance = maxsize
    remainder = "end"

    __init__ (self, distance, remainder):
      self.distance = distance
      self.remainder = remainder
 
    def calcpoint(self,x0, x1, y0, y1, d):
        a = x1 - x0
        b = y1 - y0

        if a == 0:
            xn = x1

            if b > 0:
                yn = y0 + d
            else:
                yn = y0 - d
            return (xn, yn)

        theta = degrees(math.atan(abs(b)/abs(a)))

        if a > 0 and b > 0:
            omega = theta
        if a < 0 and b > 0:
            omega = 180 - theta
        if a < 0 and b < 0:
            omega = 180 + theta
        if a > 0 and b < 0:
            omega = 360 - theta

        if b == 0:
            yn = y1
            if a > 0:
                xn = x0 + d
            else:
                xn = x0 - d
        else:
            xn = x0 + d*math.cos(radians(omega))
            yn = y0 + d*math.sin(radians(omega))

        return (xn, yn)

    def distance(self, x0, x1, y0, y1):
        deltax = x0 - x1
        deltay = y0 - y1
        d2 = (deltax)**2 + (deltay)**2
        d = math.sqrt(d2)
        return d

    def densify(self, geometry):
        gtype = geometry.GetGeometryType()
        if  not (gtype == ogr.wkbLineString or gtype == ogr.wkbMultiLineString):
            raise Exception("The densify function only works on linestring or multilinestring geometries")

        g = ogr.Geometry(ogr.wkbLineString)

        # add the first point
        x0 = geometry.GetX(0)
        y0 = geometry.GetY(0)
        g.AddPoint(x0, y0)

        for i in range(1,geometry.GetPointCount()):
            threshold = self.distance
            x1 = geometry.GetX(i)
            y1 = geometry.GetY(i)
            if not x0 or not y0:
                raise Exception("First point is null")
            d = self.distance(x0, x1, y0, y1)

            if self.remainder.upper() == "UNIFORM":
                if d != 0.0:
                    threshold = float(d)/math.ceil(d/threshold)
                else:
                    # duplicate point... throw it out
                    continue
            if (d > threshold):
                if self.remainder.upper() == "UNIFORM":
                    segcount = int(math.ceil(d/threshold))

                    dx = (x1 - x0)/segcount
                    dy = (y1 - y0)/segcount

                    x = x0
                    y = y0
                    for p in range(1,segcount):
                        x = x + dx
                        y = y + dy
                        g.AddPoint(x, y)

                elif self.remainder.upper() == "END":
                    segcount = int(math.floor(d/threshold))
                    xa = None
                    ya = None
                    for p in range(1,segcount):
                        if not xa:
                            xn, yn = self.calcpoint(x0,x1,y0,y1,threshold)
                            d = self.distance(x0, xn, y0, yn)
                            xa = xn
                            ya = yn
                            g.AddPoint(xa,ya)
                            continue
                        xn, yn = self.calcpoint(xa, x1, ya, y1, threshold)
                        xa = xn
                        ya = yn
                        g.AddPoint(xa,ya)

                elif self.remainder.upper() == "BEGIN":

                    # I think this might put an extra point in at the end of the
                    # first segment
                    segcount = int(math.floor(d/threshold))
                    xa = None
                    ya = None
                    #xb = x0
                    #yb = y0
                    remainder = d % threshold
                    for p in range(segcount):
                        if not xa:
                            xn, yn = self.calcpoint(x0,x1,y0,y1,remainder)

                            d = self.distance(x0, xn, y0, yn)
                            xa = xn
                            ya = yn
                            g.AddPoint(xa,ya)
                            continue
                        xn, yn = self.calcpoint(xa, x1, ya, y1, threshold)
                        xa = xn
                        ya = yn
                        g.AddPoint(xa,ya)

            g.AddPoint(x1,y1)
            x0 = x1
            y0 = y1

        return g
