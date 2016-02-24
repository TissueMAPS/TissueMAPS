import rtree
import cPickle

class FastRtree(rtree.Rtree):
    def dumps(self, obj):
        return cPickle.dumps(obj, -1)

class MapObject:
    def __init__(self, id, outline, centroid):
        self.id = id
        self.outline = outline
        self.centroid = centroid
