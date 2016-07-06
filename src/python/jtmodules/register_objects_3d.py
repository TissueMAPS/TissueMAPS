import logging
import numpy as np

logger = logging.getLogger(__name__)


def register_objects_3d(label_image):
    '''
    Jterator module for registering segmented objects for use by other
    (measurement) modules downstream in the pipeline.

    Parameters
    ----------
    label_image: numpy.ndarray[int32]
        labeled image where pixel values encode objects IDs

    Returns
    -------
    Dict[str, numpy.ndarray[int32]]
        * "objects": label_image
    '''
    
    siz = label_image.shape
    output1 = []
    
    if (len(siz) == 2):
        return {'objects': label_image}
        
    elif (len(siz) > 2):
        
        for i in range(0,siz[2]):
            
            label_image1 = label_image[:,:,i]
            output1.append(label_image1) 
            
        output = np.dstack(output1) 
        return {'objects': output}