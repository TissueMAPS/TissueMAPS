import numpy as np
import pandas as pd


def relate_objects_3d(parents_image, children_image):
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
    children_image: numpy.ndarray
        label image containing the children objects

    Returns
    -------
    Dict[str, pandas.Series]
        * "parent_ids": parent object ID for each children object
    '''
    
    siz = parents_image.shape
    output1 = []
    
    if (len(siz) == 2):
        children_ids = np.unique(children_image[children_image != 0])

        parent_ids = list()
        for j in children_ids:
            p = np.unique(parents_image[children_image == j])[0]
            parent_ids.append(p)
    
        return {'parent_ids': pd.Series(parent_ids, name='parent_ids')}

    elif (len(siz) > 2):
        
        for i in range(0,siz[2]):
            
            children_image1 = children_image[:,:,i]
            parents_image1 = parents_image[:,:,i]
            
            children_ids = np.unique(children_image1[children_image1 != 0])

            parent_ids = list()
            for j in children_ids:
                p = np.unique(parents_image1[children_image1 == j])[0]
                parent_ids.append(p)
            
            output1.append(pd.Series(parent_ids, name='parent_ids'))
            
        return {'parent_ids': output1}