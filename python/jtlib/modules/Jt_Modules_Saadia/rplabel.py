# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

import numpy as np
from skimage.measure import regionprops, label

def rplabel(imLogical=None,imIntensity=None,Property=None,logarithm=None,*args,**kwargs):

    imLabel=label(imLogical)
    
    logarithimic_mask =  imLabel.copy()
    logarithimic_mask[logarithimic_mask>0] = 1
        
    if imIntensity.shape == 0:
        imIntensity=np.zeros(imLogical.shape).astype(np.int64)
    
    i1 = 0
    for region in regionprops(imLabel):
            i1 = i1 + 1 
            if len(logarithm) >0 :
                if logarithm == np.str('two'):
                    logarithimic_mask[imLabel == i1] = np.log2(region[Property])
                if logarithm == np.str('ten'):
                    logarithimic_mask[imLabel == i1] = np.log10(region[Property])
                if logarithm == np.str('nat'):
                    logarithimic_mask[imLabel == i1] = np.log(region[Property])
            else:
                logarithimic_mask[imLabel == i1] = region[Property]
       
    return logarithimic_mask

