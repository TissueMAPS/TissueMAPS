import numpy as np
from skimage.measure import label, regionprops
import cv2
import scipy as sp
import PIL
from matplotlib import pyplot as plt
import jtlib as jtlib
from scipy import ndimage as ndi
import math 
import calculate_object_selection_features as calculate_object_features
import ismember as ismember

def separate_clumps(label_image=None,intensity_image=None,perimeter_trace=None,
                    max_eqiv_radius=None,min_eqiv_angle=None,objsize_thres=None,
                    num_region_threshold=None,*args,**kwargs):
    

    object_ids = np.unique(label_image[:])
    
    distance_to_object_max = 3    

    i1 = 0
    north1 = list()
    south1 = list()
    west1 = list()
    east1 = list()
    siz = label_image.shape

    for region in regionprops(label_image):
        i1 = i1 + 1 
        
        north11 = np.floor(region.bbox[1] - distance_to_object_max - 1)
        if north11 < 1:
            north11 = 1
        north1.append(north11)
       
        south11 = np.ceil(region.bbox[1] + region.bbox[3] +  
                distance_to_object_max + 1)
        if south11 > siz[0]:
            south11 = siz[0]
        south1.append(south11)
        
        west11 = np.floor(region.bbox[0] - distance_to_object_max - 1)
        if west11 < 1:
            west11 = 1
        west1.append(west11)
            
        east11 = np.ceil(region.bbox[0] + region.bbox[2] + 
                 distance_to_object_max + 1)
        if east11 > siz[1]:
            east11 = siz[1]
        east1.append(east11)
    
    
    if i1 <= 0:
        cut_mask=np.zeros(label_image.shape)
        return cut_mask
    
    
    
    cut_mask = np.zeros(label_image.shape)
    if len(object_ids) > 0:
        for i in range(1, len(object_ids)):
            current_preim_props = perimeter_trace[i]
            
            
            concave_regions = label(current_preim_props)
            num_concave = np.unique(concave_regions)
            props_concave_region = np.zeros(num_concave)
            pixelsconcave_regions = list(num_concave)
            
            for j in num_concave:
                props_current_region = current_preim_props[concave_regions == j,:]
                normal_vectors = props_current_region[:,3:4]
                norm_curvature = props_current_region[:,9]
#                props_concave_region[j] = np.max(norm_curvature)
#                props_concave_region[j] = np.mean(norm_curvature)
                maxima_indices = (norm_curvature == np.max(norm_curvature))
                
                props_concave_region[j,3:4] = np.mean(
                                              normal_vectors[maxima_indices,:],1)
                
                props_concave_region[j,5:6] = np.mean(normal_vectors,1)
                first_maximum_index = maxima_indices(1)
                last_maximum_index = maxima_indices(-1)
                mean_maximum_index = np.round(
                                  (last_maximum_index + first_maximum_index)/2)
                
                props_concave_region[j,7:8] = props_current_region[
                                                mean_maximum_index,1:2]
                                                
                props_concave_region[j,9:10] = props_current_region[np.round(
                                              (np.shape(
                                              props_current_region)[0]+1)/2),1:2]
                
                props_concave_region[j,11] = np.sum(norm_curvature)
                props_concave_region[j,12] = len(norm_curvature)/np.sum(
                                                                norm_curvature)
                props_concave_region[j,13] = j
                pixelsconcave_regions[j] = props_current_region[:,1:2]
                
            if np.shape(props_concave_region)[0] > num_region_threshold:
                raise ValueError(
                "object skipped because it has too many concave regions \\n")
                continue
            
            qualifying_regions_mask = (props_concave_region[:,11] >= min_eqiv_angle) \
                            and (props_concave_region[:,12] <= max_eqiv_radius)
            
            selected_regions = props_concave_region[qualifying_regions_mask,:]
            cut_coord_list = selected_regions[:,[7,8]]
            region_index = (np.arange(len(cut_coord_list))).T
            if np.shape(cut_coord_list)[0] > 1:
                rcut = cut_coord_list[:,1] + 1 - north1[i]
                ccut = cut_coord_list[:,2] + 1 - west1[i]
                minicut_coord_list = np.array([rcut,ccut])
                immini = label_image[north1[i]:south1[i],west1[i]:east1[i]]
                imbwmini = immini == i
                imintmini = intensity_image[north1[i]:south1[i],west1[i]:east1[i]]
                imintmini[~imbwmini] = 0
                padsize = np.array([1,1])
                padbw = np.pad(imbwmini,padsize)
                padint = np.pad(imintmini,padsize)
                padws = cv2.watershed(PIL.imageops.invert(padint))
                padws[np.logical_not(padbw)] = 0
                imcurrentprelines = np.zeros(np.shape(padint))
                imcurrentprelines[~padws] = padbw[~padws]
                imcurrentprelines[~padbw] = 0
                imcurrentprelines2 = imcurrentprelines
                imcurrentprelines2[~padbw] = 5
                
                f = np.array([[0,1,0],[1,0,1],[0,1,0]])
                imcurrentlinesandnodes = sp.misc.imfilter(imcurrentprelines2,f)
                imcurrentlinesandnodes[~imcurrentprelines2] = 0
                imcurrentlinesandnodes[~padbw] = 0
                imcurrentlines = label(imcurrentlinesandnodes < 3 
                                 and imcurrentlinesandnodes > 0,4)
                lineprops = regionprops(imcurrentlines)
                lineareas = lineprops.area
                lineids = np.unique(imcurrentlines[:])
                lineids[lineids == 0] = []
                imcurrentnodes = label(imcurrentlinesandnodes > 2,4)
                nodesprops = regionprops(imcurrentnodes)
                nodescentroids = nodesprops.centroid
                nodesids = np.unique(imcurrentnodes[:])
                nodesids = nodesids[2:-1].T
                f = [[[0,1,0],[0,0,0],[0,0,0]],[[0,0,0],[1,0,0],[0,0,0]], \
                     [[0,0,0],[0,0,1],[0,0,0]],[[0,0,0],[0,0,0],[0,1,0]]]
                     
                displacedlines = sp.misc.imfilter(imcurrentlines,f)
                displacedlines = np.concatenate(3,displacedlines[:])
                nodeType = np.zeros(np.shape(nodesids))
                matnodeslines = np.zeros(len(nodesids),len(lineareas))
                for inode in len(nodesids):
                    tmpid = nodesids[inode]
                    tmpix = imcurrentnodes == tmpid
                    temptype = np.unique(imcurrentlinesandnodes[tmpix])
                    nodeType[inode] = np.max(temptype) > 5
                    tmpix = np.tile(tmpix,(4,1))
                    templineids = np.unique(displacedlines[tmpix])
                    templineids[templineids == 0] = []
                    matnodeslines[inode,templineids.T] = templineids.T
                matnodesnodes = np.zeros(len(nodesids))
                matnodesnodeslabel = np.zeros(len(nodesids))
                for inode in len(nodesids):
                    tmplines = np.unique(matnodeslines[inode,:])
                    tmplines[tmplines == 0] = []
                    for l in tmplines.reshape(-1):
                        tmpnodes = matnodeslines[:,l] > 0
                        matnodesnodes[inode,tmpnodes] = lineareas[l]
                        matnodesnodeslabel[inode,tmpnodes] = l
                        
                matnodesnodes[np.ravel_multi_index((nodesids,nodesids), 
                            dims=(len(nodesids),len(nodesids)), order='C')] = 0
                matnodesnodeslabel[np.ravel_multi_index((nodesids,nodesids), 
                            dims=(len(nodesids),len(nodesids)), order='C')] = 0
#                matnodesnodeslabel[np.ravel_multi_index(
#                    [len(nodesids),len(nodesids)],(nodesids,nodesids))] = 0
                
                node_to_test = nodesids[(nodeType>0)]
                
                if kwargs['debug']:
                    i,j1 = np.transpose(
                                    filter(lambda a: a !=  0, imcurrentlines))
                    #i,j1 = np.transpose(np.nonzero(imcurrentlines))
                    plt.imshow(padint)
                    plt.title(['object #'+ i])
                    plt.hold(True)
                    plt.scatter(j1,i,150)
                    plt.scatter(nodescentroids[node_to_test,1],
                                nodescentroids[node_to_test,2],2000)
                    plt.hold(False)
                    
                potentialnodescoordinates = nodescentroids[node_to_test,:]
                potentialnodescoordinates = np.round(potentialnodescoordinates)
                nodecoordlist = np.zeros(np.shape(potentialnodescoordinates))
                if len(potentialnodescoordinates) > 0  \
                    and len(minicut_coord_list) >0:
                        
                    alllines = list()
                    nodecoordlist[:,1] = potentialnodescoordinates[:,2]
                    nodecoordlist[:,2] = potentialnodescoordinates[:,1]
                    __,closestnodesindex = np.linalg.norm(
                                           nodecoordlist,minicut_coord_list)
                    closestnodesindex = np.unique(closestnodesindex[:])
                    
                    if kwargs['debug']:
                        plt.imshow(padint)
                        plt.title(['object #'+ i])
                        plt.hold(True)
                        plt.scatter(
                        minicut_coord_list[:,2],minicut_coord_list[:,1],2000)
                        plt.hold(False)
                        selectednodecoordlist = nodecoordlist[closestnodesindex,:]
                        plt.imshow(padint)
                        plt.title(['object #'+ i])
                        plt.hold(True)
                        plt.scatter(
                        selectednodecoordlist[:,2],
                        selectednodecoordlist[:,1],2000)
                        plt.hold(False)
                        
                    if len(closestnodesindex) > 0:
                        closestnodesids = node_to_test[closestnodesindex]
                        nodeixs = np.tile(closestnodesids,[len(closestnodesids),1])
                        nodeixt = np.tile(closestnodesids,[1,len(closestnodesids)])
                        nodeixs = nodeixs[:]
                        nodeixt = nodeixt[:]
                        
                        dist,path = jtlib.dijkstra(matnodesnodes > 0,
                                                   matnodesnodes,
                                                   closestnodesids,
                                                   closestnodesids,nargout=2)
                        
                        dist = dist[:].T
                        dist = filter(lambda a: a != 0, dist) and \
                               filter(lambda a: a != np.inf, dist)
                               
                        quantile_distance = np.quantile(dist)
                        thrix = filter(lambda a: a != 0, dist)  and \
                                filter(lambda a: a < quantile_distance, dist)
                                
                        nodeixs2 = nodeixs[thrix]
                        nodeixt2 = nodeixt[thrix]
                        nodescoordlist = nodescentroids[nodeixs2,:]
                        nodescoordlist = np.round(nodescoordlist)
                        nodetcoordlist = nodescentroids[nodeixt2,:]
                        nodetcoordlist = np.round(nodetcoordlist)
                        __,closestcutpointssindex = np.linalg.norm(
                                                    minicut_coord_list,
                                                    np.fliplr(nodescoordlist))
                        
                        closestcutpointssindex = closestcutpointssindex[:]
                        __,closestcutpointstindex = np.linalg.norm(
                                                    minicut_coord_list,
                                                    np.fliplr(nodetcoordlist))
                        closestcutpointstindex = closestcutpointstindex[:]
                        alllines = list()
                        for n in len(nodeixt2):
                            tmppath = path[closestnodesids == nodeixs2[n], 
                                        closestnodesids == nodeixt2[n]]
                                        
                            tmpimage = np.zeros(np.shape(imcurrentnodes))
                            t1 = ismember.ismember(imcurrentnodes,tmppath)
                            tmpimage[t1] = 1
                            for j in len(tmppath):
                                tmpimage[imcurrentlines == 
                                                matnodesnodeslabel[
                                                tmppath[j],tmppath[j+1]]] = 1
                            tmpsegmentation = padbw
                            tmpsegmentation[tmpimage > 0] = 0
                            tmpsubsegmentation = label(tmpsegmentation > 0)
                            tmpnumobjects = np.unique(tmpsubsegmentation)
                            
                            tmpsubareas = list(tmpsubsegmentation.pixelidxlist)
                            if tmpnumobjects == 2 and np.min(
                                                tmpsubareas) > objsize_thres:
                                
                                [tmpsubareas, tmpsubsolidity, tmpsub_formfactor] = \
                                calculate_object_features(tmpsegmentation)
                                
                                alllines[n].areasobj = tmpsubareas
                                alllines[n].solobj = tmpsubsolidity
                                alllines[n].formobj = tmpsub_formfactor
                                alllines[n].lineimage = tmpimage
                                alllines[n].segmimage = tmpsegmentation
                                tmpintimage = tmpimage > 0
                                tmpmaxint = np.max(padint[tmpintimage])
                                tmpmeanint = np.mean(padint[tmpintimage])
                                tmpstdint = np.std(padint[tmpintimage])
                                tmpquantint = np.quantile(padint[tmpintimage],0.75)
                                tmplength = np.sum(tmpintimage[:])
                                alllines[n].maxint = tmpmaxint
                                alllines[n].meanint = tmpmeanint
                                alllines[n].quantint = tmpquantint
                                alllines[n].stdint = tmpstdint
                                alllines[n].length = tmplength
                                tmpcentroid1 = np.round(
                                        nodescentroids[closestnodesids
                                        [closestnodesids == nodeixs2[n]],:])
                                
                                tmpcentroid2 = np.round(
                                        nodescentroids[closestnodesids
                                        [closestnodesids == nodeixt2[n]],:])
                                
                                temp1 = (tmpcentroid1[2] - tmpcentroid2[2])
                                temp2 = (tmpcentroid1[1] - tmpcentroid2[1])
                                
                                m =  temp1 / temp2
                                
                                x = list(range(np.min(
                                    [tmpcentroid1[1],tmpcentroid2[1]]),np.max(
                                    [tmpcentroid1[1],tmpcentroid2[1]])))
                                if m != -np.inf and m != np.inf and ~np.isnan(m):
                                    y = list(range(np.min(
                                    [tmpcentroid1[2],tmpcentroid2[2]]),
                                    np.max([tmpcentroid1[2],tmpcentroid2[2]])))
                                    
                                    c = tmpcentroid1[2] - m * tmpcentroid1[1]
                                    py = np.round(m.dot(x) + c)
                                    px = np.round((y - c) / m)
                                    if np.max(
                                        np.shape(tmpimage)[0])>np.max(
                                        [y,py]) and np.max(
                                        np.shape(tmpimage)[1]) > np.max([px,x]):
                                            
                                        straigtlineix = np.ravel_multi_index(
                                                np.shape(tmpimage),[y,py],[px,x])
                                    else:
                                        straigtlineix = np.nan
                                else:
                                    straigtlineix = np.nan
                                tmprim = tmpimage
                                tmprim[straigtlineix[not np.isnan(
                                                        straigtlineix)]] = 1
                                tmprim = ndi.binary_fill_holes(tmprim)
                                tmpRatio = np.sum(tmprim[:]) / len(np.unique(
                                                            straigtlineix))
                                alllines[n].straightness = tmpRatio
                                currentsourcenode = region_index[
                                                    closestcutpointssindex[n]]
                                currentTargetnode = region_index[
                                                    closestcutpointstindex[n]]
                                                    
                                regiona = current_preim_props[concave_regions 
                                        == selected_regions
                                        [currentsourcenode,13],[1,2,3,4]]
                                        
                                regionb = current_preim_props[concave_regions 
                                        == selected_regions
                                        [currentTargetnode,13],[1,2,3,4]]
                                allangles = np.zeros(np.shape(regiona)[0]
                                                        ,np.shape(regionb)[0])
                                for l in np.shape(regiona)[0]:
                                    for m in np.shape(regionb)[0]:
                                        connectingVectorab = regionb[m,1:2] - \
                                                                regiona[l,1:2]
                                        
                                        t1 = connectingVectorab/np.linalg.norm(  
                                                             connectingVectorab)
                                        connectingVectorab = t1
                                                            
                                        connectingVectorba = -connectingVectorab
                                        angledeviationa = math.acos(math.dot(
                                                          regiona[l,3:4],
                                                          connectingVectorab))
                                        angledeviationb = math.acos(math.dot(
                                                          regionb[m,3:4],
                                                          connectingVectorba))
                                        
                                        t1 = (angledeviationa+angledeviationb)/2
#                                        meanangledeviation = t1
                                        allangles[l,m] = np.pi - t1
                                allangles = np.real(allangles)
                                tmpangle = np.max(allangles[:])
                                alllines[n].angle = tmpangle
                else:
                    alllines = list()
                    
                if len(alllines[:]) > 0:
                    alllines = filter(None, alllines) 
                    if len(alllines) == 1:
                        bestlinesindex = 1
                    else:
                        if kwargs['debug']:
                            alllinesimage = np.zeros(np.shape(padint))
                            for d in len(alllines):
                                alllinesimage[alllines[d].lineimage > 0] = 1
                            i,j1 = np.transpose(filter(
                                            lambda a: a != 0, alllinesimage))
                            #i,j1 = np.transpose(np.nonzero(alllinesimage))
                            plt.imshow(padint)
                            plt.title(['object #'+ i])
                            plt.hold(True)
                            plt.scatter(j1,i,150)
                            plt.scatter(
                                selectednodecoordlist[:,2],
                                selectednodecoordlist[:,1],3000)
                            plt.hold(False)
                        optfunc = lambda a,b,c,d,e,f,g,h: \
                            a - 2 * b - c - d - e + 2 * f - g - 2 * h
                        linemaxint = alllines.maxint
                        linemeanint = alllines.meanint
                        linestraight = alllines.straightness
                        lineangle = alllines.angle
                        linelength = alllines.length
                        linequantint = alllines.quantint
                        solobjs = alllines.solobj
                        formobjs = alllines.formobj
                        smallindex = np.min((alllines.areasobj),[],2,nargout=2)
                        solobj = np.zeros(np.shape(solobjs)[0])
                        formobj = np.zeros(np.shape(formobjs)[0])
                        for k in np.shape(solobjs)[0]:
                            solobj[k,1] = solobjs[k,smallindex[k]]
                            formobj[k,1] = formobjs[k,smallindex[k]]
                            
                        bestlines = optfunc[solobj,formobj,linemeanint.dot(100),
                                        linemaxint.dot(10),linequantint.dot(10),
                                        lineangle,linestraight/10,linelength/10]
                                            
                        bestlinesindex = sorted(bestlines, reverse=True)
                    if kwargs['debug']:
                        bestlineimage = np.zeros(np.shape(padint))
                        bestlineimage[alllines[
                                        bestlinesindex[1]].lineimage > 0] = 1
                        i,j1 = np.transpose(
                                        filter(lambda a: a != 0, bestlineimage))
                        #i,j1 = np.transpose(np.nonzero(bestlineimage))
                        plt.imshow(padint)
                        plt.title(['object #'+ i])
                        plt.hold(True)
                        plt.scatter(j1,i,150)
                    if len(bestlinesindex) > len(alllines):
                        raise ValueError(
                                "Failed to find a more optimal cut for object")
                    else:
                        imbestline = alllines[bestlinesindex[1]].lineimage
                        if np.max(imbestline[:]) > 0:
                            imbestline = imbestline[(padsize[1]+1):
                                        (-1 - padsize[1]),
                                        (padsize[2] + 1):(-1 - padsize[2])]
                                        
                            rmini,cmini = np.transpose(
                                            filter(lambda a: a != 0, imbwmini))
                            #rmini,cmini = np.transpose(np.nonzero(imbwmini))
                            wmini = np.ravel_multi_index(
                                    np.shape(imbwmini),(rmini,cmini))
                            r = rmini - 1 + north1[i]
                            c = cmini - 1 + west1[i]
                            w = np.ravel_multi_index(np.shape(cut_mask),(r,c))
                            cut_mask[w] = imbestline[wmini]
    cut_mask = cut_mask > 0
    kernel = np.ones((3,3),np.uint8)
    opening = cv2.morphology(cut_mask,cv2.morph_open,kernel, iterations = 2)
    cut_mask = cv2.dilate(opening,kernel,iterations=3)
    return cut_mask