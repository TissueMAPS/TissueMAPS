
# Created on 25-March-2016 by Dr. Saadia Iftikhar, saadia.iftikhar@fmi.ch
# ---------------------------------------------------------------------


from skimage.measure import label, regionprops

def removeSmallObjects(ThresholdImage=None,AreaThreshold=None,*args,**kwargs):
    
     label_image = label(ThresholdImage)
     
     mask = label_image.copy()
     
     mask[mask>0] = 255

     i1 = 0
     for region in regionprops(label_image):
         
        i1 = i1 + 1 

        if region.area < AreaThreshold:
            mask[label_image == i1] = 0
     
     label_im = label(mask)
     
     OutputImage = mask
     
     return OutputImage, label_im