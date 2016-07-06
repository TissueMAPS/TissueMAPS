# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------

from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label
from skimage.measure import regionprops
from scipy import ndimage as ndi
import numpy as np
import skimage as sk 
from skimage.morphology import watershed, binary_dilation
from matplotlib import pyplot as plt

def segment_secondary(orig_image=None,prelim_primary_label_matrix_image=None,
                     edited_primary_label_matrix_image=None,th_correction=None,
                     minimum_th=None,maximum_th=None,*args,**kwargs):
    
      
    use_as_label_in_case_no_cackground_present = \
                                            prelim_primary_label_matrix_image
        
    if np.any(prelim_primary_label_matrix_image == 0):
        original_segmentation_has_background = 1 
    else:
        original_segmentation_has_background = 0
    
    num_ths_to_test = len(th_correction)
    th_array = np.array(num_ths_to_test, dtype = object)

    th_array = threshold_otsu(orig_image)
    th_array1 = np.zeros(len(th_correction))
    
    if num_ths_to_test > 1:
        for k in range(2,num_ths_to_test):
            refth = th_array
            th_array1[k] = (refth * th_correction[k]) /  (th_correction[0]) 
            
    numeric_ths = th_array1
    
    numeric_ths = filter(lambda a: a > maximum_th, numeric_ths) \
                        and filter(lambda a: a < minimum_th, numeric_ths)
                        
    numeric_ths = np.unique(numeric_ths)
    numeric_ths = sorted(numeric_ths, reverse = True)
    
    th_array = np.array(numeric_ths, dtype=object)
    num_ths_to_test = len(th_array1)
    
    thresh = threshold_otsu(edited_primary_label_matrix_image)
    edited_primary_binary_image = np.int32(
                                    edited_primary_label_matrix_image > thresh)
       
    bw = np.int32(prelim_primary_label_matrix_image > 0)
    cleared = bw.copy()
    clear_border(cleared)

    borders = np.logical_xor(bw, cleared)
    label_image1 = label(borders)
    boder_obj_ids=np.unique(label_image1)
        
    prelim_primary_binary_image = np.zeros(edited_primary_binary_image.shape)

    f = np.int32(map(lambda x: x 
        if x not in prelim_primary_label_matrix_image 
        else False, boder_obj_ids) or edited_primary_binary_image)
    
    prelim_primary_binary_image[f] = 1
    
    dilated_primary_binary_image = binary_dilation(prelim_primary_binary_image)
    
    primary_object_outlines = \
                     dilated_primary_binary_image - prelim_primary_binary_image
    
    abs_sobeled_image = np.abs(ndi.sobel(orig_image))
    
    cell_final_label_matrix_image = np.empty(num_ths_to_test, dtype = 'object')
    
    if original_segmentation_has_background == 0:
    
        final_label_matrix_image = use_as_label_in_case_no_cackground_present
        
    else:
        for k in range(1,num_ths_to_test):
            print k

            th_orig_image = np.int32(orig_image > th_array1[k])
            
            inverted_th_orig_image = 1 - th_orig_image
            
            binary_marker_image_pre = np.logical_or(prelim_primary_binary_image,  
                                                 inverted_th_orig_image)
            
            binary_marker_image = np.int32(binary_marker_image_pre)
            
            binary_marker_image[primary_object_outlines == 1] = 0
                
            overlaid = abs_sobeled_image * np.int32(binary_marker_image) 
            
            labels_in = sk.measure.label(overlaid)
            
            watershed_mask = np.logical_or(binary_marker_image, labels_in > 0)
            
            labels_out = watershed(overlaid,
                                   labels_in,
                                   np.ones((3, 3), bool),
                                   mask=watershed_mask)
                        
            black_watershed_lines_pre = labels_out
            
            black_watershed_lines = black_watershed_lines_pre 
            
            thresh1 = threshold_otsu(black_watershed_lines)
            
            secondary_objects1 = np.int32(black_watershed_lines > thresh1)
            
            label_matrix_image1 = label(secondary_objects1)
                        
            
            area_labels, area_locations = np.unique(label_matrix_image1, 
                                                    return_index=True)
                        
            actual_objects_binary_image = label_matrix_image1
            
            dilated_actual_objects_binary_image = binary_dilation(
                                                 actual_objects_binary_image)
            
            t1 = dilated_actual_objects_binary_image -  \
                                                actual_objects_binary_image
            
            actual_object_outlines = t1
            
            binary_marker_image_pre2 = np.logical_or(
                        actual_objects_binary_image, inverted_th_orig_image)
            
            binary_marker_image2 = binary_marker_image_pre2
             
            binary_marker_image2[actual_object_outlines == 1] = 0
                        
            inverted_orig_image = 1 - orig_image
                        
            marked_inverted_orig_image = \
                            inverted_orig_image * np.int32(binary_marker_image2)
            
            labels_in = label(marked_inverted_orig_image)
           
            watershed_mask = np.logical_or(binary_marker_image2, labels_in > 0)
            
            labels_out = watershed(marked_inverted_orig_image,
                                   labels_in,
                                   np.ones((3, 3), bool),
                                   mask=watershed_mask)
            
            second_watershed = np.double(labels_out)
                        
            final_binary_image_pre = second_watershed
            
            final_binary_image = ndi.binary_fill_holes(final_binary_image_pre)
            
            actual_objects_label_matrix_image3 = label(final_binary_image)
            
            labels_used, label_locations = np.unique(
                                           edited_primary_label_matrix_image, 
                                           return_index=True)
            
            actual_objects_label_matrix_image3 =  \
                                actual_objects_label_matrix_image3.ravel()
            
            
            edited_primary_label_matrix_image =  \
                                edited_primary_label_matrix_image.ravel()
 
            
            labels_used[actual_objects_label_matrix_image3[label_locations[1:-1]]
                ] = edited_primary_label_matrix_image[label_locations[1:-1]];
                                           
            
            actual_objects_label_matrix_image3 = np.reshape(
                    actual_objects_label_matrix_image3,final_binary_image.shape)
                                          
            edited_primary_label_matrix_image = np.reshape(
                    edited_primary_label_matrix_image,final_binary_image.shape)
            
            final_label_matrix_image_pre = actual_objects_label_matrix_image3
            
            final_label_matrix_image = final_label_matrix_image_pre
            
            plt.imshow(final_label_matrix_image, cmap='Greys_r')
            plt.show()
            
            final_label_matrix_image[edited_primary_label_matrix_image != 0] = \
                edited_primary_label_matrix_image[ \
                edited_primary_label_matrix_image != 0]

                                
            if np.max(final_label_matrix_image[:]) < 65535:
                cell_final_label_matrix_image[k] = np.uint16(
                                                    final_label_matrix_image)
            else:
                cell_final_label_matrix_image[k] = final_label_matrix_image
                        
        final_label_matrix_image = np.zeros(cell_final_label_matrix_image.shape
                                   , dtype = 'double')

        for k in range(1,num_ths_to_test):
            
            f1 = np.int32(
                        cell_final_label_matrix_image[k] != 65535
                        ) * cell_final_label_matrix_image[k]
            
            label3,f = np.unique(f1, return_index=True)
            
#            final_label_matrix_image[f] = cell_final_label_matrix_image[k][f]
            final_label_matrix_image = f1
        
        distance_to_dilate = 1
    
        dilated_prelim_sec_label_matrix_image_mini = binary_dilation(
                                                     final_label_matrix_image)
        
        thresh3 = threshold_otsu(dilated_prelim_sec_label_matrix_image_mini)
        
        dilated_prelim_sec_binary_image_mini = \
                            dilated_prelim_sec_label_matrix_image_mini > thresh3
            
        distances, (i, j) = ndi.distance_transform_edt(
                            final_label_matrix_image, return_indices=True)
        
        labels = np.zeros(final_label_matrix_image.shape, int)
        dilate_mask = distances <= distance_to_dilate
        labels[dilate_mask] = labels_in[i[dilate_mask], j[dilate_mask]]
                
        if (np.max(labels) == 0):
            labels = np.ones(labels.shape)
        
        expanded_relabeled_dilated_prelim_sec_image_mini =  \
                                            final_label_matrix_image * labels 
                                 
        relabeled_dilated_prelim_sec_image_mini = np.zeros(
                        expanded_relabeled_dilated_prelim_sec_image_mini.shape)
        
        relabeled_dilated_prelim_sec_image_mini[ \
                                dilated_prelim_sec_binary_image_mini] = \
                                expanded_relabeled_dilated_prelim_sec_image_mini[ \
                                dilated_prelim_sec_binary_image_mini]
                           
        abs_sobeled_image = np.abs(ndi.sobel(
                                        relabeled_dilated_prelim_sec_image_mini))
        
        edge_image = np.int32(ndi.morphology.binary_fill_holes(
                                                        abs_sobeled_image > 0))
        
        final_label_matrix_image = label(
                    relabeled_dilated_prelim_sec_image_mini * (1 - edge_image))
           
        if final_label_matrix_image.shape[1] != 0:
            has_objects = 1
        else:
            has_objects=0
            
        if has_objects == 1:
            loaded_image = final_label_matrix_image
            distance_to_object_max = 3
            i1 = 0
            north1 = list()
            south1 = list()
            west1 = list()
            east1 = list()
            siz = loaded_image.shape
        
            for region in regionprops(loaded_image):
                i1 = i1 + 1 
                
                north11 = np.floor(region.bbox[1] - distance_to_object_max - 1)
                if north11 < 1:
                    north11 = 1
                north1.append(north11)
                
                
                south11=np.ceil(region.bbox[1] + region.bbox[3] +  
                        distance_to_object_max + 1)
                if south11 > siz[0]:
                    south11 = siz[0]
                south1.append(south11)
                
                west11=np.floor(region.bbox[0] - distance_to_object_max - 1)
                if west11 < 1:
                    west11 = 1
                west1.append(west11)
                    
                east11 = np.ceil(region.bbox[0] + region.bbox[2] + 
                         distance_to_object_max + 1)
                if east11 > siz[1]:
                    east11 = siz[1]
                east1.append(east11)
                
            final_label_matrix_image2 = np.zeros(final_label_matrix_image.shape)
            
            num_objects = len(regionprops(loaded_image))
            
            
            if num_objects >= 1:
                patch_for_primary_object = np.zeros(num_objects)
                                
                for k in range(num_objects):
                    
                    n1 = np.int32(north1[k])
                    s1 = np.int32(south1[k])
                    e1 = np.int32(east1[k])
                    w1 = np.int32(west1[k])
                    
                    mini_image = final_label_matrix_image[n1:s1 , w1:e1]
                    
                    bwmini_image = np.int32(mini_image)
                    labelmini = label(bwmini_image)
                    
                    mini_image_nuclei = \
                                edited_primary_label_matrix_image[n1:s1, w1:e1]
                                
#                    bw_parent_of_interest = np.int32(mini_image_nuclei == k)
                    bw_parent_of_interest = np.int32(mini_image_nuclei > 0)
                    
                    new_child_id = label(labelmini * bw_parent_of_interest)
                    
                    if np.max(new_child_id) < 0:
                        patch_for_primary_object[k] = 1
                    else:                   

                        bw_out_cell_body = new_child_id
    
                        mini_region = regionprops(label(bw_out_cell_body))
                        
                        if len(mini_region) >= 1:
                            
                            final_label_matrix_image2[n1:s1,w1:e1] = labelmini
                        
            final_label_matrix_image = final_label_matrix_image2
        
        if final_label_matrix_image.shape[1] > 0:

            final_label_matrix_image[:,0] = final_label_matrix_image[:,1]
            final_label_matrix_image[:,-1] = final_label_matrix_image[:,-2]
            final_label_matrix_image[0,:] = final_label_matrix_image[1,:]
            final_label_matrix_image[-1,:] = final_label_matrix_image[-2,:]
            
            if has_objects == 1:
                if num_objects >= 1:

                        ids_of_objects_to_patch = np.unique(
                                                  patch_for_primary_object)
    
                        needs_to_include_primary =  np.int32(map(lambda x: x 
                                if x not in edited_primary_label_matrix_image 
                                else False, ids_of_objects_to_patch)) 
                        
                        final_label_matrix_image[needs_to_include_primary] = \
                                edited_primary_label_matrix_image[ \
                                needs_to_include_primary]
                        
                        secondarylabel_matrix_image = final_label_matrix_image
            else:
                secondarylabel_matrix_image = final_label_matrix_image
                
    return secondarylabel_matrix_image,edited_primary_binary_image,th_array
