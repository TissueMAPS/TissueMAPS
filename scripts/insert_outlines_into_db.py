"""
Example usage:

    python scripts/insert_outlines_into_db.py ../expdata/150820-Testset-CV/data.h5 --type cells

"""

import argparse
import sys
import os

import h5py
import numpy as np
import psycopg2
import shapefile

current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_dir, os.pardir))

parser = argparse.ArgumentParser()
parser.add_argument('input', help='the input hd5 file')
parser.add_argument(
    '--type', '-t', help='the object type for which a tree should be produced')
parser.add_argument('--out', help='the output file')
args = parser.parse_args()

# inputfile = args.input
inputfile = '../expdata/150820-Testset-CV/data.h5'
object_type = 'cells'
output = args.out

f = h5py.File(inputfile, 'r')
coords_by_id = f['/objects/%s/map_data/outlines/coordinates/' % object_type]

conn = psycopg2.connect(database='tissuemaps', user='robin')
cur = conn.cursor()

polywriter = shapefile.Writer(shapeType=shapefile.POLYGON)
# pointwriter = shapefile.Writer(shapeType=shapefile.POINT)

polywriter.field('obj_id', 'N')
polywriter.field('obj_type', 'C', 40)

# pointwriter.field('id', 'N')
# pointwriter.field('mapobject_type', 'C', 40)

for ident in coords_by_id:
    print 'Inserting mapobject with id %s' % ident
    # tall matrix with cols x and y
    coords = coords_by_id[ident][()]

    id = int(ident)

    polywriter.poly(parts=[coords.tolist()])
    polywriter.record(obj_id=id, obj_type=object_type)

    # centroid = coords.mean(axis=0).astype('int64')
    # pointwriter.point(centroid[0], centroid[1])
    # pointwriter.record(id=id, mapobject_type=object_type)

polywriter.save('mapobject')
# pointwriter.save('geom_poly')


print 'Done!'
cur.close()
conn.close()
f.close()
    # minx, miny = np.min(coords, axis=0)
    # maxx, maxy = np.max(coords, axis=0)
    # rectangle = np.array([
    #     [maxx, maxy],
    #     [maxx, miny],
    #     [minx, miny],
    #     [minx, maxy],
    #     [maxx, maxy]
    # ])
    # bbox = (minx, miny, maxx, maxy)
    # mapobj = MapObject(
    #     id=int(id), outline=coords, centroid=centroid, rect=rectangle)
    # idx.insert(int(id), bbox, obj=mapobj)
