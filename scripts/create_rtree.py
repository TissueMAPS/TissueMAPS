"""
Example usage:

    python scripts/create_rtree.py \\
        ../expdata/150820-Testset-CV/data.h5 \\
        --type cells \\
        --out ../expdata/150820-Testset-CV/cells_rtree

"""
import argparse
import h5py
import numpy as np

import sys
import os
current_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_dir, os.pardir))
from tmaps.mapobjects import FastRtree, MapObject

parser = argparse.ArgumentParser()
parser.add_argument('input', help='the input hd5 file')
parser.add_argument(
    '--type', '-t', help='the object type for which a tree should be produced')
parser.add_argument(
    '--out', '-o', help='the output name for the serialized rtree')
args = parser.parse_args()

inputfile = args.input
object_type = args.type
outputfile = args.out

f = h5py.File(inputfile, 'r')
coords_by_id = f['/objects/%s/map_data/outlines/coordinates/' % object_type]

print 'Creating Rtree'
idx = FastRtree(outputfile)

for id in coords_by_id:
    print 'Inserting mapobject with id %s' % id
    # tall matrix with cols x and y
    coords = coords_by_id[id][()]
    minx, miny = np.min(coords, axis=0)
    maxx, maxy = np.max(coords, axis=0)
    rectangle = np.array([
        [maxx, maxy],
        [maxx, miny],
        [minx, miny],
        [minx, maxy],
        [maxx, maxy]
    ])
    centroid = coords.mean(axis=0).astype('int64')
    bbox = (minx, miny, maxx, maxy)
    mapobj = MapObject(
        id=int(id), outline=coords, centroid=centroid, rect=rectangle)
    idx.insert(int(id), bbox, obj=mapobj)

print 'Done!'
f.close()
