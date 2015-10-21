import numpy as np
from jtlib import plotting


def relate_objects(parent_objects_image, parent_objects_name,
                   children_objects_image, children_objects_name, **kwargs):
    '''
    Jterator module for relating objects.

    Children objects are supposed to lie within the area of their parents,
    which implies that the size of a child object has to be the same or smaller
    than that of the corresponding parent object. Consequently, a parent object
    can have multiple children, but a child can only have one parent.

    The module saves the "ParentName" and "ParentId" for child objects.

    Parameters
    ----------
    parent_objects_image: numpy.ndarray
        label image containing the parent objects
    parent_objects_name: str
        name of the parent objects
    children_objects_image: numpy.ndarray
        label image containing the children objects
    children_objects_name: str
        name of the children objects
    config: dict
        configuration settings
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    children_ids = np.unique(children_objects_image)
    children_ids = children_ids[children_ids != 0]

    data = dict()
    parent_ids = list()
    for i in children_ids:
        p = np.unique(parent_objects_image[children_objects_image == i])[0]
        parent_ids.append(p)
    data['%s_ParentName' % children_objects_name] = parent_objects_name
    data['%s_ParentId' % children_objects_name] = parent_ids
    plotting.writedata(data, kwargs['data_file'])
