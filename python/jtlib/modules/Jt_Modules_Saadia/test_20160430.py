# -*- coding: utf-8 -*-
"""
Created on Fri Apr 15 10:56:02 2016

@author: saadiaiftikhar
"""
#!/Users/saadiaiftikhar/miniconda2/bin/python
import numpy as np
#import matplotlib.pyplot as plt
#import matplotlib.patches as mpatches

from skimage import data
from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.morphology import closing, square
from skimage.measure import regionprops
from skimage.color import label2rgb
from skimage import data, io, filters,feature
import cv2
import os, glob
from scipy import ndimage as ndi
import numpy as np
import skimage as sk
import removeSmallObjects_Saadia as removeSmallObjects_Saadia
#import calculateThresholdLevel_Saadia
import PIL.ImageOps 
from skimage.morphology import watershed
import scipy as sp
from skimage.feature import peak_local_max
import segmentSecondary as segmentSecondary

#path = '/Volumes/cv7000s$/Users/iftisaad/TM_Test_Data/Corrected_Images/'
path = '/Users/saadiaiftikhar/Documents/Markus_Data_Samples/'

searchString = path + '*_c002_*.tif'

for f in glob.glob(searchString):
	filename, file_extension = os.path.splitext(f)
	if f.endswith(".tif"):
         Input_filename = os.path.join(path,f) # source file 
         imIntensity = cv2.imread(Input_filename, cv2.IMREAD_UNCHANGED) 
         siz1 = imIntensity.shape    
    
        thresh = 130
        ImSize=imIntensity.shape
        thresh_image = imIntensity> thresh
        
        dilated_image = sk.morphology.binary_dilation(thresh_image)
    
        borders = np.logical_xor(thresh_image, dilated_image)
        
        [mask,label_image1] = removeSmallObjects_Saadia.removeSmallObjects_Saadia(ThresholdImage=borders.copy(), AreaThreshold=100)
        
        filled_holes_image = ndi.morphology.binary_fill_holes(mask)
        label_image = sk.measure.label(filled_holes_image.copy(), background=0)
        
        
#        print(np.max(editedPrimaryLabelMatrixImage))
        
        searchString1 = path + '*_c004_*.tif'

        for f1 in glob.glob(searchString1):
            filename1, file_extension1 = os.path.splitext(f1)
            if f1.endswith(".tif"):
                Input_filename1 = os.path.join(path,f1) # source file 
                print(Input_filename1)
                imIntensity1 = cv2.imread(Input_filename1, cv2.IMREAD_UNCHANGED) 
                siz2 = imIntensity1.shape   
                
                prelimPrimaryLabelMatrixImage = label_image1 
                thresholdCorrection = [100,150,200]
                origImage = imIntensity1
                maximumThreshold = 10
                minimumThreshold = 0
                editedPrimaryLabelMatrixImage = label_image 
                
                [secondaryLabelMatrixImage,editedPrimaryBinaryImage,thresholdArray] = segmentSecondary.segmentSecondary(origImage,prelimPrimaryLabelMatrixImage,editedPrimaryLabelMatrixImage,thresholdCorrection,minimumThreshold,maximumThreshold)

                    
        s1 = filename+'_Labelled_Image'+file_extension
        labelled_image_filename = os.path.join(path,s1) 
#        cv2.imwrite(labelled_image_filename, label_image)
        
        s2 = filename+'_Output_Image'+file_extension
        output_image_filename = os.path.join(path,s2) 
        cv2.imwrite(output_image_filename, secondaryLabelMatrixImage) 
#        
#        s3 = filename+'_Output_Image_Log'+file_extension
#        output_image_filename_log = os.path.join(path,s3) 
#        cv2.imwrite(output_image_filename_log, logarithimic_mask) 
        
#plt.show()

