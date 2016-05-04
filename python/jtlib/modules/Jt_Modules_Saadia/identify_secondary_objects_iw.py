# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

import numpy as np
import jtlib as jtlib
from matplotlib import pyplot as plt
import skimage as sk
from scipy import ndimage as ndi
import removeSmallObjects as removeSmallObjects

def identify_secondary_objects_iw(input_label_image=None,input_image=None,correction_factors=None,min_threshold=None,*args,**kwargs):
    
    if input_image.dtype != np.str('integer'):
        print("Input Image must have type integer.")
        
    if input_image.dtype == np.str("uint16"):
        input_image = sk.img_as_uint(input_image)
        min_threshold = sk.img_as_uint(min_threshold)
    else:
        if input_image.dtype == np.str("uint8"):
            input_image = sk.img_as_ubyte(input_image)
            min_threshold = sk.img_as_ubyte(min_threshold)
        else:
            print("Argument input_image must have type uint8 or uint16.")
            
    if input_label_image.dtype == np.str("logical"):
        print("Argument input_label_image must be a labeled image.")
        
    if input_label_image.dtype != np.str("integer"):
        print("Argument input_label_image must have type integer.")
        
    if input_label_image.dtype == np.str("int32"):
        print("Argument input_label_image  must have type int32.")
        
    input_label_image = input_label_image
    
    max_threshold = 1

    output_label_image=jtlib.segmentSecondary(input_image,input_label_image,input_label_image,correction_factors,min_threshold,max_threshold)
    
    if args[4]:
        
        out_mask = ndi.binary_fill_holes(output_label_image)
        
        dilated_image = sk.morphology.binary_dilation(out_mask)
    
        borders = np.logical_xor(out_mask, dilated_image)
        
        [mask,label_image] = removeSmallObjects.removeSmallObjects(ThresholdImage=borders.copy(), AreaThreshold=100)
                
        labeled_cells=sk.color.colorlabel.label2rgb(sk.measure.label(label_image))
        
        fig = plt.figure()
        fig.plt.subplot(2,2,1)
        fig.plt.imshow(input_image,[np.quantile(input_image[:],0.01),np.quantile(input_image[:],0.99)])
        fig.plt.title('Outlines of identified objects')
        fig.plt.subplot_(2,1,2)
        fig.plt.imshow(labeled_cells)
        plt.title('Identified objects')
        
    output_label_image = output_label_image
    
    return output_label_image
