
# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------


from skimage.measure import label, regionprops
import numpy as np

def remove_small_objects_3d(threshold_image=None,area_threshold=None,*args,**kwargs):
    
     siz = threshold_image.shape
     output1 = []
     output2 = []
    
     if (len(siz) == 2):
        
         label_image = label(threshold_image)
     
         mask = label_image.copy()
     
         mask[mask>0] = 255

         i1 = 0
         for region in regionprops(label_image):
         
            i1 = i1 + 1 

            if region.area < area_threshold:
                mask[label_image == i1] = 0
     
         label_im = label(mask)
     
         output_image = mask
     
         return output_image, label_im
     
     elif (len(siz) > 2):
        
        for i in range(0,siz[2]):
            
             label_image = label(threshold_image[:,:,i])
      
             mask = label_image.copy()
     
             mask[mask>0] = 255

             i1 = 0
             for region in regionprops(label_image):
         
                i1 = i1 + 1 

                if region.area < area_threshold:
                    mask[label_image == i1] = 0
     
             output1.append(label_image) 
            
             label_im  = np.dstack(output1) 
             
             output2.append(mask) 
            
             output_image  = np.dstack(output2)
     
             # output = {'label_image': output}    
             return output_image, label_im
            