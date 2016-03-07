class ToolResponse(object):
    pass


class LabelResponse(ToolResponse):
    def __init__(self, ids, labels, mapobject_name):
        self.ids = ids
        self.labels = labels
        self.mapobject_name = mapobject_name


class SimpleResponse(ToolResponse):
    pass
