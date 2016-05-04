# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.measure import regionprops
from scipy import ndimage as ndi
import numpy as np
import skimage as sk
import PIL.ImageOps 
from skimage.morphology import watershed
import scipy as sp
from skimage.feature import peak_local_max
from scipy.sparse import *
from scipy import *
from scipy.stats import mode
import os, glob
import cv2

def segmentSecondary(origImage=None,prelimPrimaryLabelMatrixImage=None,editedPrimaryLabelMatrixImage=None,thresholdCorrection=None,minimumThreshold=None,maximumThreshold=None,*args,**kwargs):
    
    UseAsLabelInCaseNoBackgroundPresent = prelimPrimaryLabelMatrixImage
        
    if np.any(prelimPrimaryLabelMatrixImage == 0):
        originalSegmentationHasBackground = 1 
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
       
    bw = np.int32(prelimPrimaryLabelMatrixImage > 0)
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
    
    AbsSobeledImage = np.abs(ndi.sobel(origImage))
    
    cellFinalLabelMatrixImage = np.empty(numThresholdsToTest, dtype = 'object')
    
    if originalSegmentationHasBackground == 0:
    
        FinalLabelMatrixImage = UseAsLabelInCaseNoBackgroundPresent
        
    else:
        for k in range(1,numThresholdsToTest):

            ThresholdedOrigImage = np.int32(origImage > thresholdArray1[k])
            
            InvertedThresholdedOrigImage = 1 - ThresholdedOrigImage
            
            BinaryMarkerImagePre = np.logical_or(PrelimPrimaryBinaryImage , InvertedThresholdedOrigImage)
            
            BinaryMarkerImage = np.int32(BinaryMarkerImagePre)
            
            BinaryMarkerImage[PrimaryObjectOutlines == 1]=0
                
            Overlaid = AbsSobeledImage * np.int32(BinaryMarkerImage) 
            
            labels_in = sk.measure.label(Overlaid)
    
            #distance = ndi.distance_transform_edt(Overlaid)
            
            #local_maxi = peak_local_max(distance, indices=False, footprint=np.ones((3, 3)),labels=Overlaid)
            
            #markers = ndi.label(local_maxi)[0]
            
            #labels = watershed(-distance, markers, mask=Overlaid)  
            
            watershed_mask = np.logical_or(BinaryMarkerImage, labels_in > 0)
           # watershed_mask = np.logical_and(watershed_mask, mask)
            
            labels_out = watershed(Overlaid,
                                   labels_in,
                                   np.ones((3, 3), bool),
                                   mask=watershed_mask)
            
            BlackWatershedLinesPre = labels_out
            
            BlackWatershedLines=BlackWatershedLinesPre 
            
            thresh1 = threshold_otsu(BlackWatershedLines)
            
            SecondaryObjects1 = np.int32(BlackWatershedLines>thresh1)
            
            LabelMatrixImage1 = label(SecondaryObjects1)
                        
            
            area_labels, area_locations = np.unique(LabelMatrixImage1, return_index=True)
            
#            area_locations = np.reshape(np.ravel(area_locations), (LabelMatrixImage1.shape))          
#            area_locations = filter(lambda a: a != 0, LabelMatrixImage1)
#            
#            area_labels = LabelMatrixImage1[:,area_locations]
#            b1 = np.int32(PrelimPrimaryBinaryImage[:,area_locations])
            
#            map1 = np.array([0,np.max(csr_matrix(area_locations,area_labels,b1))])
            
#            ActualObjectsBinaryImage = map1[LabelMatrixImage1 + 1]
            
            ActualObjectsBinaryImage = LabelMatrixImage1
            
            DilatedActualObjectsBinaryImage = sk.morphology.binary_dilation(ActualObjectsBinaryImage)
            
            ActualObjectOutlines = DilatedActualObjectsBinaryImage - ActualObjectsBinaryImage
            
            BinaryMarkerImagePre2 = np.logical_or(ActualObjectsBinaryImage , InvertedThresholdedOrigImage)
            
            BinaryMarkerImage2 = BinaryMarkerImagePre2
             
            BinaryMarkerImage2[ActualObjectOutlines == 1] = 0
            
#            InvertedOrigImage = PIL.ImageOps.invert(origImage)
                        
            InvertedOrigImage = 1 - origImage
                        
            MarkedInvertedOrigImage = InvertedOrigImage * np.int32(BinaryMarkerImage2)
            
            labels_in = sk.measure.label(MarkedInvertedOrigImage)

#            distance = ndi.distance_transform_edt(MarkedInvertedOrigImage)
#            
#            local_maxi = peak_local_max(distance, indices=False, footprint=np.ones((3, 3)),labels=MarkedInvertedOrigImage)
#            
#            markers = ndi.label(local_maxi)[0]
#            
#            labels = watershed(-distance, markers, mask=MarkedInvertedOrigImage)  
            
            watershed_mask = np.logical_or(BinaryMarkerImage2, labels_in > 0)
           # watershed_mask = np.logical_and(watershed_mask, mask)
            
            labels_out = watershed(MarkedInvertedOrigImage,
                                   labels_in,
                                   np.ones((3, 3), bool),
                                   mask=watershed_mask)
            
            SecondWatershed = np.double(labels_out)
            
#            area_locations2 = filter(lambda a: a != 0, SecondWatershed)
#            
#            area_labels2 = SecondWatershed[area_locations2]
#            
#            map2 = np.array([0,np.max(sp.sparse.csr_matrix(area_locations2,area_labels2,editedPrimaryBinaryImage[area_locations2]))])
#            
#            FinalBinaryImagePre = map2[SecondWatershed + 1]
            
            FinalBinaryImagePre = SecondWatershed
            
            FinalBinaryImage = ndi.binary_fill_holes(FinalBinaryImagePre)
            ActualObjectsLabelMatrixImage3 = label(FinalBinaryImage)
                        
            LabelsUsed, LabelLocations = np.unique(editedPrimaryLabelMatrixImage, return_index=True)
                        
            #LabelsUsed = np.zeros(editedPrimaryLabelMatrixImage.shape)
            #LabelLocations = np.zeros(editedPrimaryLabelMatrixImage.shape)
      
#            LabelsUsed[ActualObjectsLabelMatrixImage3[LabelLocations[1:]]] = editedPrimaryLabelMatrixImage[LabelLocations[1:]]
            
            FinalLabelMatrixImagePre = LabelsUsed[ActualObjectsLabelMatrixImage3]
            FinalLabelMatrixImage = FinalLabelMatrixImagePre
            
            FinalLabelMatrixImage[editedPrimaryLabelMatrixImage != 0] = editedPrimaryLabelMatrixImage[editedPrimaryLabelMatrixImage != 0]
            
            if np.max(FinalLabelMatrixImage[:]) < 65535:
                cellFinalLabelMatrixImage[k] = np.uint16(FinalLabelMatrixImage)
            else:
                cellFinalLabelMatrixImage[k] = FinalLabelMatrixImage
                        
        FinalLabelMatrixImage = np.zeros(cellFinalLabelMatrixImage.shape,dtype = 'double')

        for k in range(1,numThresholdsToTest):
            
            f1 = np.int32(cellFinalLabelMatrixImage[k] != 65535) * cellFinalLabelMatrixImage[k]
            label3,f = np.unique(f1, return_index=True)
            
#            FinalLabelMatrixImage[f] = cellFinalLabelMatrixImage[k][f]
            FinalLabelMatrixImage = f1
        
        DistanceToDilate = 1
    
        DilatedPrelimSecObjectLabelMatrixImageMini = sk.morphology.binary_dilation(FinalLabelMatrixImage)
        
        thresh3 = threshold_otsu(DilatedPrelimSecObjectLabelMatrixImageMini)
        
        DilatedPrelimSecObjectBinaryImageMini = DilatedPrelimSecObjectLabelMatrixImageMini>thresh3
            
        distances, (i, j) = ndi.distance_transform_edt(FinalLabelMatrixImage, return_indices=True)
        
        Labels = np.zeros(FinalLabelMatrixImage.shape, int)
        dilate_mask = distances <= DistanceToDilate
        Labels[dilate_mask] = labels_in[i[dilate_mask], j[dilate_mask]]
        
#        ExpandedRelabeledDilatedPrelimSecObjectImageMini = np.zeros(FinalLabelMatrixImage.shape, int)
        
        if (np.max(Labels) == 0):
            Labels = np.ones(Labels.shape)
        
        ExpandedRelabeledDilatedPrelimSecObjectImageMini = FinalLabelMatrixImage * Labels 
                                 
        RelabeledDilatedPrelimSecObjectImageMini = np.zeros(ExpandedRelabeledDilatedPrelimSecObjectImageMini.shape)
        
        RelabeledDilatedPrelimSecObjectImageMini[DilatedPrelimSecObjectBinaryImageMini] = ExpandedRelabeledDilatedPrelimSecObjectImageMini[DilatedPrelimSecObjectBinaryImageMini]
                           
        AbsSobeledImage = np.abs(ndi.sobel(RelabeledDilatedPrelimSecObjectImageMini))
        edgeImage = np.int32(ndi.morphology.binary_fill_holes(AbsSobeledImage > 0))
        
        FinalLabelMatrixImage = label(RelabeledDilatedPrelimSecObjectImageMini * (1-edgeImage))
           
        if FinalLabelMatrixImage.shape[1] != 0:
            hasObjects = 1
        else:
            hasObjects=0
            
        if hasObjects == 1:
            loadedImage = FinalLabelMatrixImage
            distanceToObjectMax=3
#            BoxPerObj = list()
            i1 = 0
            N = list()
            S = list()
            W = list()
            E = list()
            SIZ = loadedImage.shape
        
            for region in regionprops(loadedImage):
                i1 = i1 + 1 
#                BoxPerObj.append(region.bbox)
                
                N1=np.floor(region.bbox[1] - distanceToObjectMax - 1)
                if N1 < 1:
                    N1 = 1
                N.append(N1)
               
                S1=np.ceil(region.bbox[1] + region.bbox[3] + distanceToObjectMax + 1)
                if S1 > SIZ[0]:
                    S1 = SIZ[0]
                S.append(S1)
                
                W1=np.floor(region.bbox[0] - distanceToObjectMax - 1)
                if W1 < 1:
                    W1 = 1
                W.append(W1)
                    
                E1=np.ceil(region.bbox[0] + region.bbox[2] + distanceToObjectMax + 1)
                if E1 > SIZ[1]:
                    E1 = SIZ[1]
                E.append(E1)
                
            FinalLabelMatrixImage2 = np.zeros(FinalLabelMatrixImage.shape)
            
            numObjects = len(regionprops(loadedImage))
            
            if numObjects >= 1:
                patchForPrimaryObject = np.zeros(numObjects)
                                
#                for k in range(numObjects):
                for k in range(100,150):
                    
                    n1 = np.int32(N[k])
                    s1 = np.int32(S[k])
                    e1 = np.int32(E[k])
                    w1 = np.int32(W[k])
                    
                    miniImage = FinalLabelMatrixImage[n1:s1 , w1:e1]
                    
                    bwminiImage = np.int32(miniImage)
                    labelmini = label(bwminiImage)
                    
                    miniImageNuclei = editedPrimaryLabelMatrixImage[n1:s1 , w1:e1]
#                    bwParentOfInterest = np.int32(miniImageNuclei == k)
                    bwParentOfInterest = np.int32(miniImageNuclei > 0)
                    
                    NewChildID = label(labelmini * bwParentOfInterest)
                    
                    if np.max(NewChildID) < 0:
                        patchForPrimaryObject[k] = 1
                    else:                   
                        WithParentIX = np.unique(NewChildID)  
#                        bwOutCellBody = labelmini * np.int32(labelmini == WithParentIX)                        
#                        bwOutCellBody = filter(lambda a: a.any == WithParentIX, labelmini)
                        bwOutCellBody = NewChildID
    
                        mini_region = regionprops(label(bwOutCellBody))
                        
                        if len(mini_region) >= 1:
                            
#                            r1 = mini_region[0].coords[0]
#                            c = mini_region[0].coords[1]

#                            r = np.int32(r1[0] - 1 + N[k])                      
#                            c = np.int32(r1[1] - 1 + W[k])
                                
#                            w = np.ravel_multi_index((r, c), dims=(FinalLabelMatrixImage2.shape), order='C')
#                            w = np.ravel_multi_index(FinalLabelMatrixImage2,(r,c))
                            
#                            FinalLabelMatrixImage2[r,c] = k
                            FinalLabelMatrixImage2[n1:s1 , w1:e1] = labelmini
                        
            FinalLabelMatrixImage = FinalLabelMatrixImage2
        
        if FinalLabelMatrixImage.shape[1] > 0:

            FinalLabelMatrixImage[:,0] = FinalLabelMatrixImage[:,1]
            FinalLabelMatrixImage[:,-1] = FinalLabelMatrixImage[:,-2]
            FinalLabelMatrixImage[0,:] = FinalLabelMatrixImage[1,:]
            FinalLabelMatrixImage[-1,:] = FinalLabelMatrixImage[-2,:]
            
            if hasObjects == 1:
                if numObjects >= 1:
#                    if any(patchForPrimaryObject):
#                        IDsOfObjectsToPatch = filter(lambda a: a != 0, patchForPrimaryObject)
                        IDsOfObjectsToPatch = np.unique(patchForPrimaryObject)
    
                        needsToIncludePrimary =  np.int32(map(lambda x: x if x not in editedPrimaryLabelMatrixImage else False, IDsOfObjectsToPatch)) 
                        
                        FinalLabelMatrixImage[needsToIncludePrimary] = editedPrimaryLabelMatrixImage[needsToIncludePrimary]
                        
                        secondaryLabelMatrixImage = FinalLabelMatrixImage
            else:
                secondaryLabelMatrixImage = FinalLabelMatrixImage
                
    return secondaryLabelMatrixImage,editedPrimaryBinaryImage,thresholdArray
