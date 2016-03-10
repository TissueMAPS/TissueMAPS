import numpy as np


def relate_objects(parents_image, parents_name,
                   children_image, children_name, plot=False):
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
    plot: bool, optional
        whether a plot should be generated (default: ``False``)
    '''
    children_ids = np.unique(children_image[children_image != 0])

    parent_ids = list()
    for i in children_ids:
        p = np.unique(parents_image[children_image == i])[0]
        parent_ids.append(p)

    return {'parent_ids': parent_ids, 'figure': ''}

