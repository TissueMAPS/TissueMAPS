import scipy.ndimage as ndi
import numpy as np

def expand_objects_3d(label_image, n, plot=False):
    '''Expands objects in `label_image` by `n` pixels along each axis.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.int32]
        image where each connected pixel component is labeled with a unique
        non-zero number
    n: int
        number of pixels by which each connected component should be expanded
    plot: bool, optional
        whether a plot should be generated (default: ``False``)

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.int32] or str]
        "expanded_objects": label image with expanded objects
        "figure": html string in case `plot` is ``True``
    '''
    # NOTE: code from CellProfiler module "expandorshrink"
    
    siz = label_image.shape
    output1 = []
    
    if (len(siz) == 2):
        
        background = label_image == 0
        distance, (j, k) = ndi.distance_transform_edt(
                                            background, return_indices=True)
        expanded_image = label_image.copy()
        mask = background & (distance < n)
        expanded_image[mask] = label_image[j[mask], k[mask]]
        
        output = {'expanded_image': expanded_image}
        output['figure'] = str()
        return output
    
    elif (len(siz) > 2):
        
        for i in range(0,siz[2]):
            
            label_image1 = label_image[:,:,i]
            
            background = label_image1 == 0
            distance, (j, k) = ndi.distance_transform_edt(
                                            background, return_indices=True)
            expanded_image = label_image1.copy()
            mask = background & (distance < n)
            expanded_image[mask] = label_image1[j[mask], k[mask]]
            
            output1.append(expanded_image)
        
        output = np.dstack(output1) 
        output = {'expanded_image': output}
        output['figure'] = str()
        return output