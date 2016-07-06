
# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

from skimage.measure import regionprops
import numpy as np

def calculate_object_selection_features(objects=None,*args,**kwargs):

    solidity = list()
    area = list()
    p = list()
    tmp = list()
    
    for region in regionprops(objects):

        solidity.append(region.solidity)
        area.append(region.area)
        p.append(region.perimeter) 
        n1 = 4 * np.pi * region.area
        n2 = (region.perimeter + 1)
        if ~np.isnan(np.log2((n1/n2))):
            tmp.append(np.log2((n1/n2)))
        else: 
            tmp.append(0)

    tmp[tmp < 0]=0
    formfactor=tmp

    return area,solidity,formfactor
