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
import calculateThresholdLevel_Saadia
import PIL.ImageOps 
from skimage.morphology import watershed
import scipy as sp
from skimage.feature import peak_local_max

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
        
        prelimPrimaryLabelMatrixImage = label_image 
        thresholdCorrection = [100,150,200]
        origImage = imIntensity
        maximumThreshold = 10
        minimumThreshold = 0
        editedPrimaryLabelMatrixImage = label_image 
        
        UseAsLabelInCaseNoBackgroundPresent = prelimPrimaryLabelMatrixImage
    
        if np.any(prelimPrimaryLabelMatrixImage == 0):
            originalSegmentationHasBackground =1 
        else:
            originalSegmentationHasBackground = 0
        
        numThresholdsToTest = len(thresholdCorrection)
        thresholdArray = np.array(numThresholdsToTest, dtype = object)
        ThresholdMethod = 'Otsu Global'
        pObject = 10
        
        thresholdArray = threshold_otsu(origImage)
        thresholdArray1 = np.zeros(len(thresholdCorrection))
        
        if numThresholdsToTest > 1:
            for k in range(2,numThresholdsToTest):
                refThreshold = thresholdArray
                thresholdArray1[k] = refThreshold * thresholdCorrection[k] / thresholdCorrection[0]
                
        numericThresholds = thresholdArray1
        
        numericThresholds = filter(lambda a: a > maximumThreshold, numericThresholds) and filter(lambda a: a < minimumThreshold, numericThresholds)
        numericThresholds = np.unique(numericThresholds)
        numericThresholds = sorted(numericThresholds, reverse = True)
        
        thresholdArray = np.array(numericThresholds, dtype=object)
        numThresholdsToTest = len(thresholdArray1)
        
        thresh = threshold_otsu(editedPrimaryLabelMatrixImage)
        editedPrimaryBinaryImage = np.int32(editedPrimaryLabelMatrixImage > thresh)
           
        bw = prelimPrimaryLabelMatrixImage > 0
        cleared = bw.copy()
        clear_border(cleared)
        label_image = label(cleared)
        borders = np.logical_xor(bw, cleared)
        label_image1 = label(borders)
        BoderObjIDs=np.unique(label_image1)
            
        PrelimPrimaryBinaryImage = np.zeros(editedPrimaryBinaryImage.shape)
        
        f = np.int32(map(lambda x: x if x not in prelimPrimaryLabelMatrixImage else False, BoderObjIDs) or editedPrimaryBinaryImage)
        
        PrelimPrimaryBinaryImage[f] = 1
        
        DilatedPrimaryBinaryImage = sk.morphology.binary_dilation(PrelimPrimaryBinaryImage)
        
        PrimaryObjectOutlines = DilatedPrimaryBinaryImage - PrelimPrimaryBinaryImage
        
        dx = ndi.sobel(origImage, 0)  
        dy = ndi.sobel(origImage, 1)  
        mag = np.hypot(dx, dy)  
        mag *= 255.0 / np.max(mag)  
        AbsSobeledImage = mag
        
        cellFinalLabelMatrixImage = np.empty(numThresholdsToTest, dtype = 'object')
        
        if originalSegmentationHasBackground == 0:
        
            FinalLabelMatrixImage = UseAsLabelInCaseNoBackgroundPresent
            
        else:
            for k in range(1,numThresholdsToTest):

                ThresholdedOrigImage = np.int32(origImage > thresholdArray1[k])
                
                InvertedThresholdedOrigImage = 1-ThresholdedOrigImage
                
                BinaryMarkerImagePre = np.logical_or(PrelimPrimaryBinaryImage , InvertedThresholdedOrigImage)
                
                BinaryMarkerImage = np.int32(BinaryMarkerImagePre)
                
                BinaryMarkerImage[PrimaryObjectOutlines == 1]=0
                    
                Overlaid = AbsSobeledImage * np.int32(BinaryMarkerImage)    

                distance = ndi.distance_transform_edt(Overlaid)
                
                local_maxi = peak_local_max(distance, indices=False, footprint=np.ones((3, 3)),labels=Overlaid)
                
                markers = ndi.label(local_maxi)[0]
                
                labels = watershed(-distance, markers, mask=Overlaid)   
                
                BlackWatershedLinesPre = labels
                
                BlackWatershedLines=BlackWatershedLinesPre 
                
                thresh1 = threshold_otsu(BlackWatershedLines)
                
                SecondaryObjects1 = np.int32(BlackWatershedLines>thresh1)
                
                LabelMatrixImage1 = label(SecondaryObjects1)
                
                area_locations = filter(lambda a: a != 0, LabelMatrixImage1)
                
                area_labels = LabelMatrixImage1[area_locations]
                
                map1 = np.array([0,np.max(sp.sparse.csr_matrix(area_locations,area_labels,PrelimPrimaryBinaryImage[area_locations]))])
                
                ActualObjectsBinaryImage = map1[LabelMatrixImage1 + 1]
                
                DilatedActualObjectsBinaryImage = sk.morphology.binary_dilation(ActualObjectsBinaryImage)
                
                ActualObjectOutlines = DilatedActualObjectsBinaryImage - ActualObjectsBinaryImage
                
                BinaryMarkerImagePre2 = np.logical_or(ActualObjectsBinaryImage , InvertedThresholdedOrigImage)
                
                BinaryMarkerImage2 = BinaryMarkerImagePre2
                 
                BinaryMarkerImage2[ActualObjectOutlines == 1] = 0
                
                InvertedOrigImage = PIL.ImageOps.invert(origImage)
                
                MarkedInvertedOrigImage = InvertedOrigImage * np.int32(BinaryMarkerImage2)
                
                distance = ndi.distance_transform_edt(MarkedInvertedOrigImage)
                
                local_maxi = peak_local_max(distance, indices=False, footprint=np.ones((3, 3)),labels=MarkedInvertedOrigImage)
                
                markers = ndi.label(local_maxi)[0]
                
                labels = watershed(-distance, markers, mask=MarkedInvertedOrigImage)  
                
                SecondWatershed = np.double(labels)
                
                area_locations2 = filter(lambda a: a != 0, SecondWatershed)
                
                area_labels2 = SecondWatershed[area_locations2]
                
                map2 = np.array([0,np.max(sp.sparse.csr_matrix(area_locations2,area_labels2,editedPrimaryBinaryImage[area_locations2]))])
                
                FinalBinaryImagePre = map2[SecondWatershed + 1]
                
                FinalBinaryImage = ndi.binary_fill_holes(FinalBinaryImagePre)
                ActualObjectsLabelMatrixImage3 = label(FinalBinaryImage)
                
                LabelsUsed,LabelLocations = np.unique(editedPrimaryLabelMatrixImage, return_index=True)
  
                LabelsUsed[ActualObjectsLabelMatrixImage3[LabelLocations[1:-2]] + 1] = editedPrimaryLabelMatrixImage[LabelLocations[1:-2]]
                
                FinalLabelMatrixImagePre = LabelsUsed[ActualObjectsLabelMatrixImage3 + 1]
                FinalLabelMatrixImage = FinalLabelMatrixImagePre
                
                FinalLabelMatrixImage[editedPrimaryLabelMatrixImage != 0] = editedPrimaryLabelMatrixImage[editedPrimaryLabelMatrixImage != 0]
                
                if np.max(FinalLabelMatrixImage[:]) < 65535:
                    cellFinalLabelMatrixImage[k] = np.uint16(FinalLabelMatrixImage)
                else:
                    cellFinalLabelMatrixImage[k] = FinalLabelMatrixImage
                    
            FinalLabelMatrixImage = np.zeros(cellFinalLabelMatrixImage.shape,dtype = 'double')
            
            for k in range(numThresholdsToTest):
                
                f = cellFinalLabelMatrixImage[k] != 0
                FinalLabelMatrixImage[f] = cellFinalLabelMatrixImage[k][f]
            
            DistanceToDilate = 1

            DilatedPrelimSecObjectLabelMatrixImageMini = sk.morphology.binary_dilation(FinalLabelMatrixImage)
            
            thresh3 = threshold_otsu(DilatedPrelimSecObjectLabelMatrixImageMini)
            
            DilatedPrelimSecObjectBinaryImageMini = DilatedPrelimSecObjectLabelMatrixImageMini>thresh3

            indices = np.zeros(((np.ndim(FinalLabelMatrixImage),) + FinalLabelMatrixImage.shape), dtype=np.int32)
            
            distance = ndi.distance_transform_edt(FinalLabelMatrixImage>0, return_indices=True, indices=indices)
            
            Labels = indices
            
            if (np.max(Labels) == 0):
                Labels=np.ones(Labels.shape)
            
            ExpandedRelabeledDilatedPrelimSecObjectImageMini = FinalLabelMatrixImage[Labels]
                                     
            RelabeledDilatedPrelimSecObjectImageMini = np.zeros(ExpandedRelabeledDilatedPrelimSecObjectImageMini.shape)
            
            RelabeledDilatedPrelimSecObjectImageMini[DilatedPrelimSecObjectBinaryImageMini] = ExpandedRelabeledDilatedPrelimSecObjectImageMini[DilatedPrelimSecObjectBinaryImageMini]
                               
            dx = ndi.sobel(RelabeledDilatedPrelimSecObjectImageMini, 0)  
            dy = ndi.sobel(RelabeledDilatedPrelimSecObjectImageMini, 1)  
            mag = np.hypot(dx, dy)  
            if mag.shape[1] != 0:
                mag *= 255.0 / np.max(mag) 
                AbsSobeledImage = np.abs(mag)
                edgeImage=AbsSobeledImage > 0
                FinalLabelMatrixImage=RelabeledDilatedPrelimSecObjectImageMini*(~edgeImage)
            else:
                FinalLabelMatrixImage=RelabeledDilatedPrelimSecObjectImageMini
            
           
            if FinalLabelMatrixImage.shape[1] != 0:
                hasObjects = 1
            else:
                hasObjects=0
                
            if hasObjects == 1:
                loadedImage = FinalLabelMatrixImage
                distanceToObjectMax=3
                
                BoxPerObj = []
                i1 = 0
                N = []
                S = []
                W = []
                E = []
                SIZ = loadedImage.shape
                
                for region in regionprops(loadedImage):
                    i1 = i1 + 1 
                    BoxPerObj.append(region.bbox)
                    
                    N1=np.floor(region.bbox[1] - distanceToObjectMax - 1)
                    if N1<1:
                        N1=1
                    N.append(N1)
                   
                    S1=np.ceil(region.bbox[1] + region.bbox[3] + distanceToObjectMax + 1)
                    if S1 > SIZ[0]:
                        S1=SIZ[0]
                    S.append(S1)
                    
                    W1=np.floor(region.bbox[0] - distanceToObjectMax - 1)
                    if W1<1:
                        W1=1
                    W.append(W1)
                    E1=np.ceil(region.bbox[0] + region.bbox[2] + distanceToObjectMax + 1)
                    if E1 > SIZ[1]:
                        E1=SIZ[1]
                    E.append(E1)
                    
                FinalLabelMatrixImage2 = np.zeros(FinalLabelMatrixImage.shape)
                
                numObjects = len(regionprops(loadedImage))
                
                if numObjects >= 1:
                    patchForPrimaryObject = np.zeros(numObjects)
                    
                    for k in range(numObjects):
                        n1 = N[k]
                        s1 = S[k]
                        e1 = E[k]
                        w1 = W[k]
                        
                        miniImage=FinalLabelMatrixImage.crop(n1,s1,w1,e1)
                        
                        bwminiImage = miniImage > 0
                        labelmini = label(bwminiImage)
                        miniImageNuclei = editedPrimaryLabelMatrixImage.crop(n1,s1,w1,e1)
                        bwParentOfInterest = miniImageNuclei == k
                        
                        NewChildID = labelmini[bwParentOfInterest]
                        
                        if len(NewChildID)>0:
                            patchForPrimaryObject[k] = 1
                        else:
                            NewChildID = filter(lambda a: a > 0, NewChildID)
                            
                            WithParentIX = np.mod(NewChildID)
                            
                            bwOutCellBody = filter(lambda a: a == WithParentIX, labelmini)

                            r,c = filter(lambda a: a != 0, bwOutCellBody)
 
                            r = r - 1 + N[k]
                            
                            c = c - 1 + W[k]
                            
                            w = np.ravel_multi_index(np.size(FinalLabelMatrixImage2),(r,c))
                            
                            FinalLabelMatrixImage2[w] = k
                            
                FinalLabelMatrixImage = FinalLabelMatrixImage2
            
            if FinalLabelMatrixImage.shape[1] != 0:
                FinalLabelMatrixImage[:,1] = FinalLabelMatrixImage[:,2]
                FinalLabelMatrixImage[:,-1] = FinalLabelMatrixImage[:,-1]
                FinalLabelMatrixImage[1,:] = FinalLabelMatrixImage[2,:]
                FinalLabelMatrixImage[-1,:] = FinalLabelMatrixImage[-1,:]
                
                if hasObjects == 1:
                    if numObjects >= 1:
                        if any(patchForPrimaryObject):
                            IDsOfObjectsToPatch = filter(lambda a: a != 0, patchForPrimaryObject)

                            needsToIncludePrimary = map(lambda x: x if x not in editedPrimaryLabelMatrixImage else False, IDsOfObjectsToPatch) 
                            
                            FinalLabelMatrixImage[needsToIncludePrimary] = editedPrimaryLabelMatrixImage[needsToIncludePrimary]
                            
                            secondaryLabelMatrixImage = FinalLabelMatrixImage
            else:
                 secondaryLabelMatrixImage = FinalLabelMatrixImage               
            
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

