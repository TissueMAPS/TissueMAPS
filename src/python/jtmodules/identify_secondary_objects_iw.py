# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

import skimage as sk
import segment_secondary as segment_secondary

def identify_secondary_objects_iw(input_label_image=None,input_image=None,
                                  correction_factors=None,min_threshold=None):

    if input_image.dtype == "uint16":
        input_image = sk.img_as_uint(input_image)
        min_threshold = sk.img_as_uint(min_threshold)
    else:
        if input_image.dtype == 'uint8':
            input_image = sk.img_as_ubyte(input_image)
            min_threshold = sk.img_as_ubyte(min_threshold)
        else:
            raise TypeError(
                        "Argument input_image must have type uint8 or uint16.")
        
    input_label_image = input_label_image
    
    max_threshold = 1

    output_label_image = segment_secondary.segment_secondary(
                                                input_image,input_label_image,
                                                input_label_image,
                                                correction_factors,
                                                min_threshold, max_threshold)
        
    output_label_image = output_label_image
    
    return output_label_image
