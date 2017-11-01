from osgeo import ogr
from osgeo import osr
from math import sqrt
import sys

def IsDangle (line_geometry, dangle_length):
    return line_geometry.Length() <= dangle_length

def LineSegmentCount(line_geometry_list):
    line_count = 0
    for street_line in line_geometry_list:
        line_count += 1
    return line_count

def ExtendLine (street_segment_geom, at_start, start_point_tup, end_point_tup, length):

    start_point = ogr.Geometry(ogr.wkbPoint)
    end_point = ogr.Geometry(ogr.wkbPoint)
    start_point.AddPoint(start_point_tup[0], start_point_tup[1])
    end_point.AddPoint(end_point_tup[0], end_point_tup[1])
    lenAB = sqrt(pow(start_point.GetX() - end_point.GetX(), 2.0) + pow(start_point.GetY() - end_point.GetY(), 2.0))
    newPoint = ogr.Geometry(ogr.wkbPoint)
    newPoint.AddPoint( end_point.GetX() + (end_point.GetX() - start_point.GetX()) / lenAB * length,
                       end_point.GetY() + (end_point.GetY() - start_point.GetY()) / lenAB * length)

    extended_line = ogr.Geometry(ogr.wkbLineString)
    # Add this newly extended point as either the first point on the LINESTRING or the last
    if (at_start):
        extended_line.AddPoint(newPoint.GetX(), newPoint.GetY())
    for i in range(0, street_segment_geom.GetPointCount()):
        extended_line.AddPoint(street_segment_geom.GetPoint(i)[0], street_segment_geom.GetPoint(i)[1])
    if (not at_start):
        extended_line.AddPoint(newPoint.GetX(), newPoint.GetY())

    return extended_line

def LineNodeIndexInConnector(street_segment_geom, conector_segment_geom):
    """
    Determine whether a node in the street_segment_geom is within
    the buffer of the connector_segment_geom.  If so, return the
    index of the Points on the line that is within the buffer.
    :param street_segment_geom:
    :param conector_segment_geom:
    :return:
    """

    buffered_connector = conector_segment_geom.Buffer(0.0000001)
    print("Var type of buffer {}".format(buffered_connector.GetGeometryType()))
    for i in range(0, street_segment_geom.GetPointCount()):
        point = ogr.Geometry(ogr.wkbPoint)
        point.AddPoint(street_segment_geom.GetPoint(i)[0],street_segment_geom.GetPoint(i)[1])
        print("Node {} is within {}".format(i, point.Within(buffered_connector)))
        if point.Within(buffered_connector):
            return i

    return -1

def ExtendStreetStreetSegment(street_segment_geom, connector_segment_geom):
    # is one of the line nodes in the connector buffer, we'll extend that end of the line
    line_node_index = LineNodeIndexInConnector(street_segment_geom, connector_segment_geom)
    print("Line Node Index: {}".format(line_node_index))
    if (line_node_index > -1):
        if (line_node_index == 0):
            start_point = street_segment_geom.GetPoint(1)
            end_point = street_segment_geom.GetPoint(0)
        else:
            start_point = street_segment_geom.GetPoint(line_node_index - 1)
            end_point = street_segment_geom.GetPoint(line_node_index)
        street_segment_geom = ExtendLine(street_segment_geom,
                                         (line_node_index == 0),
                                         start_point, end_point, 0.0000005)

        return street_segment_geom

    return None


def UnionBlockCentroidStreetLines():

    ogr.UseExceptions()


    # create the spatial reference, WGS84
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    street_segment_geom = ogr.CreateGeometryFromWkt('LINESTRING (-118.720517 34.035146,-118.720423 34.035102,-118.720348 '
                                                    '34.035079,-118.720194 34.035041,-118.720007 34.035013,-118.719805 '
                                                    '34.034969,-118.719633 34.034941,-118.719485 34.034919,-118.719275 '
                                                    '34.034892,-118.719135 34.034879,-118.71906 34.03488,-118.718967 '
                                                    '34.034894,-118.718872 34.034949)')

    connector_segment_geom = ogr.CreateGeometryFromWkt('LINESTRING (-118.7184635353147 34.03795005627166,-118.71887206743176 34.0349485045679)')

    street_segment_geom.AssignSpatialReference(srs)
    connector_segment_geom.AssignSpatialReference(srs)

    if (street_segment_geom.Intersects(connector_segment_geom)):
        census_street_geom = street_segment_geom.Union(connector_segment_geom)
    else:
        print("    We didn't get any intersections for this one, trying extend street segment")
        street_segment_geom = ExtendStreetStreetSegment(street_segment_geom, connector_segment_geom)
        if street_segment_geom != None:
            if (street_segment_geom.Intersects(connector_segment_geom)):
                census_street_geom = street_segment_geom.Union(connector_segment_geom)
            else:
                print("WEe still don't got it !!!! {}".format(street_segment_geom))


def main(argv):

    UnionBlockCentroidStreetLines ()

if __name__ == "__main__":
  main(sys.argv[1:])