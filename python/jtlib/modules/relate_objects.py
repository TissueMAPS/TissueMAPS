import numpy as np
from tmlib.writers import DatasetWriter


def relate_objects(parents_image, parents_name,
                   children_image, children_name, **kwargs):
    '''
    Jterator module for relating objects.

    Children objects are supposed to lie within the area of their parents,
    which implies that the size of a child object has to be the same or smaller
    than that of the corresponding parent object. Consequently, a parent object
    can have multiple children, but a child can only have one parent.

    Parameters
    ----------
    parents_image: numpy.ndarray
        label image containing the parent objects
    parents_name: str
        name of the parent objects
    children_image: numpy.ndarray
        label image containing the children objects
    children_name: str
        name of the children objects
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    children_ids = np.unique(children_image[children_image != 0])

    parent_ids = list()
    for i in children_ids:
        p = np.unique(parents_image[children_image == i])[0]
        parent_ids.append(p)

    if len(children_ids) > 0:

        group_name = '/objects/%s/segmentation' % children_name

        with DatasetWriter(kwargs['data_file']) as f:
            f.write('%s/parent_name' % group_name,
                    data=parents_name)
            f.write('%s/parent_objects_ids' % group_name,
                    data=parent_ids)
