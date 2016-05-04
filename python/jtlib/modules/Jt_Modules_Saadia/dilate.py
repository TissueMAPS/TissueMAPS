# Created on 12-April-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

import numpy as np
import cv2

def dilate_Saadia(image_array, N, iterations): 
    
    kernel = np.zeros((N,N), dtype=np.uint8)
    
    kernel[(N-1)/2,:] = 1
    
    dilated_image = cv2.dilate(image_array / 255, kernel, iterations=iterations)

    kernel = np.zeros((N,N), dtype=np.uint8)
    
    kernel[:,(N-1)/2] = 1
    
    dilated_image = cv2.dilate(dilated_image, kernel, iterations=iterations)
    
    return dilated_image
