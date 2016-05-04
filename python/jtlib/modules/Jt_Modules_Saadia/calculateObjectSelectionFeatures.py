
# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

from skimage.measure import regionprops
import numpy as np

def calculateObjectSelectionFeatures(Objects=None,*args,**kwargs):
   
   
    i1 = 0
    Solidity = list()
    Area = list()
    P = list()
    tmp = list()
    
    for region in regionprops(Objects):
        i1 = i1 + 1 
        Solidity.append(region.solidity)
        Area.append(region.area)
        P.append(region.perimeter) 
        n1 = 4*np.pi*region.area
        n2 = (region.perimeter+1)
        if ~np.isnan(np.log2((n1/n2))):
            tmp.append(np.log2((n1/n2)))
        else: 
            tmp.append(0)
        #print(tmp)
    tmp[tmp < 0]=0
    FormFactor=tmp

    return Area,Solidity,FormFactor
