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
#import ismember 
from scipy import ndimage as ndi
import numpy as np
import skimage as sk
import dilate_Saadia as dilate
import removeSmallObjects_Saadia as removeSmallObjects_Saadia
from PIL import Image

path = '/Volumes/cv7000s$/Users/iftisaad/TM_Test_Data/Corrected_Images/'

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
        
        [mask,label_image] = removeSmallObjects_Saadia.removeSmallObjects_Saadia(ThresholdImage=borders.copy(), AreaThreshold=100)
#        label_image = sk.measure.label(borders.copy(), background=0)
        
        n1 = np.unique(label_image)
        #print(n1)
        
#        LabelLocations = []
#        LabelsUse = []
#        i1 = 0            
#        for region in regionprops(label_image):
#            i1 = i1 + 1 
#            coord = region.coords 
#            LabelLocations = coord
#            LabelsUsed= i1
#        
#        print(LabelLocations[1:-2])
        #print(LabelsUsed)
        
        #ObjectIDs=np.unique(label_image[:])
        #print(ObjectIDs)
#        pixel_acces_object = label_image.load()
#        print(pixel_acces_object)
        
        indices = np.zeros(((np.ndim(label_image),) + label_image.shape), dtype=np.int32)
        distance = ndi.distance_transform_edt(label_image>0, return_indices=True, indices=indices)
        Labels = indices[1,:,:] 
        #print(Labels.shape)
                
        if np.max(Labels[:]) == 0:
            Labels=np.ones(Labels.shape)
#        

#        #print(Labels.shape[0])
#        #print(Labels.shape[1])
#        
        ExpandedRelabeledDilatedPrelimSecObjectImageMini = np.zeros(siz1)
        area_locations2 = filter(lambda a: a == Labels, label_image)
        area_labels2=label_image[area_locations2]
        
        #ExpandedRelabeledDilatedPrelimSecObjectImageMini=label_image[Labels]
#        
#
#        for i in range(Labels.shape[0]):
#            for j in range(Labels.shape[1]):
#                #print(i)
#                #print(j)
#                #print(np.int64(Labels[i, j]))
#                ExpandedRelabeledDilatedPrelimSecObjectImageMini[i, j] = label_image[Labels[i, j]]
#                
        print(ExpandedRelabeledDilatedPrelimSecObjectImageMini)
        
#        i1 = 0
#        for region in regionprops(label_image):
#            i1 = i1 + 1 
#            cnt = region.coords           
#            ObjectTrace=cnt
#            InterPixelVectors=np.diff(ObjectTrace)
           # print(InterPixelVectors)
       
        
        s1 = filename+'_Labelled_Image'+file_extension
        labelled_image_filename = os.path.join(path,s1) 
#        cv2.imwrite(labelled_image_filename, label_image)
        
        s2 = filename+'_Output_Image'+file_extension
        output_image_filename = os.path.join(path,s2) 
#        cv2.imwrite(output_image_filename, mask) 
#        
#        s3 = filename+'_Output_Image_Log'+file_extension
#        output_image_filename_log = os.path.join(path,s3) 
#        cv2.imwrite(output_image_filename_log, logarithimic_mask) 
        
#plt.show()

