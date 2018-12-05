# -*- coding: utf-8 -*-
from osgeo import ogr
from shapely.geometry import Point
from shapely.ops import split
from shapely.wkt import loads
import os
"""
***************************************************************************
    SplitLinesWithLines.py
    ---------------------
    Date                 : November 2018
    Revised              : November 2018
    Email                : cord dot thomas at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************

This script was copied from SplitLinesWithLines QGIS plugin originally
developed by Bernhard Ströbl.  I adapted it to rely only on OSGEO and 
Shapely; it currently assumes your input and outputs will be 
ESRI Shapefiles.

"""

__author__ = 'Cord Thomas'
__date__ = 'November 2018'
__version__ = "0.1"
__maintainer__ = "Cord Thomas"
__email__ = "cord.thomas@gmail.com"
__status__ = "Prototype"

class SplitLinesWithLines(object):

  def convert_ogr_line_to_shapely(self, ogr_geometry):

    return loads(ogr_geometry.ExportToWkt())

  def convert_shapely_line_to_ogr(self, shapely_geometry):
    """Convert a shapely geometry object to a GDAL/OGR
    geometry."""
    return ogr.CreateGeometryFromWkt(shapely_geometry.wkt)

  def copy_feature_attribute_values(self, inFeature, outLayerDefn, outFeature):
    for i in range(0, outLayerDefn.GetFieldCount()):
      fieldName = outLayerDefn.GetFieldDefn(i).GetNameRef()
      field = inFeature.GetField(i)
      outFeature.SetField(fieldName, field)

  def convert_multilinestring_to_linestring(self, multilinestring):
    """
    Convert a multilinestring to a linestring. If the input is already
    a simple linestring, just return it.
    :param multilinestring: Expects either a multilinestring or a
    linestring
    :return: a linestring geometry
    """

    if (multilinestring.GetGeometryType() == ogr.wkbLineString):
      return multilinestring
    else:
      ls = ogr.Geometry(ogr.wkbLineString)
      for linestr in multilinestring:
        # print ('Processing MLS with line {}'.format(linestr))
        for pnt in linestr.GetPoints():
          # print ('Processing MLS with point {}'.format(pnt))
          ls.AddPoint(pnt[0], pnt[1])

      return ls

  def append_features(self, source_feature, updating_layer, updating_layer_defn, new_geom):

    new_feature = ogr.Feature(updating_layer_defn)
    self.copy_feature_attribute_values(source_feature, updating_layer_defn, new_feature)
    new_feature.SetGeometry(new_geom)
    updating_layer.CreateFeature(new_feature)

  def get_split_point(self, in_shape, split_shape):
    """Given an input line and a split line, identify the
    vertex in the input line that is the split point from
    the split line.  We will obviously not split the input
    line at the nodes, only the internal vertices.
    Returns None if no point found."""
    if len(in_shape.coords) <= 2:
      return None
    in_coords =  list(in_shape.coords)
    split_coords = list(split_shape.coords)

    for i, p in enumerate (in_coords[1:len(in_coords)-1]):
      if p in split_coords:
        return Point(p)

    return None

  def intersect_geometries(self, inFeat, inGeom, shapeLayerB, sameLayer):
    """Return a list of streets features in layer B that intersect with
    the street from layer A given a geometric buffer of 0.001 degrees.
    I would prefer to return geometries but believe they cannot be returned from
    a function because of their belonging to a feature handle.
    :param inGeom: The path to the input source
    :param shapeLayerB:
    :param sameLayer: Whether inGeom layer and shapeLayerB are the same
    :return: An array of intersecting features from layer B intersecting input geometry
    """
    intersectingLines= []
    bufferSize = 0.0001
    spatialFilterBuffer = inGeom.Buffer(bufferSize)

    shapeLayerB.SetSpatialFilter(spatialFilterBuffer)

    if shapeLayerB.GetFeatureCount() > 0:
      for feature in shapeLayerB:
        featureGeom = feature.GetGeometryRef()
        if (sameLayer and (feature.GetFID() == inFeat.GetFID())):
          continue
        if (inGeom.Intersects(featureGeom)):
          intersectingLines.append(feature)
        # else:
        #   print("    FEATURE {inf} doesn't intersect FEATURE {outf}".format(inf=feature.GetField("LINEARID"),
        #                                                                                 outf=inFeat.GetField("LINEARID")))

    shapeLayerB.SetSpatialFilter(None)
    return intersectingLines

  def is_dangle(self, line_geometry, dangle_length):
    return line_geometry.Length() <= (dangle_length + dangle_length / 10) and \
           line_geometry.Length() >= (dangle_length - dangle_length / 10)

  def split_lines_with_lines(self, input_source_a, input_source_b, outputTarget):
    """

    :param input_source_a: The path to the first input source
    :param input_source_b: The path to the second input source
    :param outputTarget: The path to the resulting split lines network
    :return:
    """

    # First handle if tilde expansion is needed
    if input_source_a[0] == '~' and not os.path.exists(input_source_a):
      input_source_a = os.path.abspath(os.path.expanduser(input_source_a))
    if input_source_b[0] == '~' and not os.path.exists(input_source_b):
      input_source_b = os.path.abspath(os.path.expanduser(input_source_b))
    if outputTarget[0] == '~' and not os.path.exists(outputTarget):
      outputTarget = os.path.abspath(os.path.expanduser(outputTarget))

    driver = ogr.GetDriverByName('ESRI Shapefile')
    shapeDataSourceA = driver.Open(input_source_a, 0)
    shapeLayerA = shapeDataSourceA.GetLayer(0)
    shapeLayerdefnA = shapeLayerA.GetLayerDefn()

    shapeDataSourceB = driver.Open(input_source_b, 0)
    shapeLayerB = shapeDataSourceB.GetLayer(0)
    shapeLayerdefnB = shapeLayerB.GetLayerDefn()

    sameLayer = input_source_a == input_source_b

    srs = shapeLayerA.GetSpatialRef()

    outputDatasource = driver.CreateDataSource(outputTarget)
    outputLayer = outputDatasource.CreateLayer(
      outputTarget.split('/')[-1].replace('.shp',''),
      srs, ogr.wkbLineString)

    # Copy the layer definition from the first input
    # layer into the output layer
    for i in range(shapeLayerdefnA.GetFieldCount()):
      outputLayer.CreateField(shapeLayerdefnA.GetFieldDefn(i))

    outLayerDefn = outputLayer.GetLayerDefn()

    outFeature = ogr.Feature(outLayerDefn)

    # result = shapeLayerA.SetAttributeFilter("LINEARID='1101576691101'")

    for inFeatA in shapeLayerA:

      inGeom = inFeatA.GetGeometryRef()
      inLines = [inGeom]

      splittingLines = self.intersect_geometries(inFeatA, inGeom, shapeLayerB, sameLayer)

      print ("We have found {} intersecting streets for {}".format(len(splittingLines), inFeatA.GetField("LINEARID")))

      if len(splittingLines) > 0:

        for splitFeature in splittingLines:
          outLines = []
          splitGeom = splitFeature.GetGeometryRef()

          while len(inLines) > 0:
            inGeom = inLines.pop()
            inShape = self.convert_ogr_line_to_shapely(self.convert_multilinestring_to_linestring(inGeom))

            splitShape = self.convert_ogr_line_to_shapely(self.convert_multilinestring_to_linestring(splitGeom))

            # Interestingly, the ogr Intersects test failed for some features
            # that Shapely finds intersected - e.g., LINEARID ﻿1101576657596
            # failed intersect test with ﻿1101576691101 from the Los Angeles
            # street centerline data
            if inShape.intersects(splitShape):

              success = False
              try:
                splitPoint = self.get_split_point(inShape, splitShape)
                if splitPoint is not None:
                  success = True
                  outSplitShapes = split(inShape, splitPoint)
              except ValueError as ve:
                print ("We have an exception: {}".format(ve))
              except Exception as ex:
                print ("We have an exception: {}".format(type(ex)))

              if success and len(outSplitShapes) > 1:
                # inLines.append(inGeom) - this statement was in the original QGIS split source, but not needed.

                for outShape in outSplitShapes:
                  inLines.append(self.convert_shapely_line_to_ogr(outShape))
              else:
                outLines.append(inGeom)

            else:
              outLines.append(inGeom)

          inLines = outLines

      for aLine in inLines:
        if aLine.Length() > 0.000001:

          self.append_features(inFeatA, outputLayer,
                               outLayerDefn,
                               aLine)

    outputLayer = None
    outputDatasource = None
    shapeDataSourceA = None
    shapeDataSourceB = None

