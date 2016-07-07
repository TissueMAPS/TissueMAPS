import numpy as np
import cv2
# import scipy as sp
# import PIL
import itertools
import collections
import mahotas as mh
import skimage as ski
import skimage.measure
import skimage.morphology
import skimage.filters
import skimage.segmentation
from shapely.geometry import asLineString
# from shapely.geometry import LineString
from matplotlib import pyplot as plt
# import jtlib as jtlib
from scipy import ndimage as ndi
import math 
import jtlib.utils
# from tmlib.image_utils import map_to_uint8
# import calculate_object_selection_features as calculate_object_features
# import ismember as ismember


def find_concave_regions(mask, size):
    '''Finds convace regions along the contour of `mask`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        mask image
    size: int
        size of the kernel used to define concavity

    Note
    ----
    Fast implementation in C++ using `OpenCV library <http://opencv.org/>`_.
    '''
    contour_img = np.zeros(mask.shape, dtype=np.uint8)
    contour_img[mask] = 255
    contour_img, contours, _ = cv2.findContours(
        contour_img,
        mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
    )
    concave_img = np.zeros(mask.shape, dtype=np.bool)
    for cnt in contours:
        hull = cv2.convexHull(cnt, returnPoints=False)
        defects = cv2.convexityDefects(cnt, hull)
        if defects is not None:
            defect_pts = np.array([
                cnt[defects[j, 0][2]][0]
                for j in xrange(defects.shape[0])
                if defects[j, 0][3]/float(256) > size
            ])
            if defect_pts.size != 0:
                concave_img[defect_pts[:, 1], defect_pts[:, 0]] = True
    return mh.label(concave_img)


def find_watershed_lines(mask, img, ksize):
    '''Finds watershed lines in the region of `img` defined by `mask`.
    The seeds for the watershed are automatically determined using thresholding
    (Otsu's method). The thereby created mask is morphologically opened using
    a squared structuring element of size `ksize`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        mask image
    img: numpy.ndarray[numpy.uint8 or numpy.uint16]
        intensity image
    ksize: int
        size of the kernel that's used to morphologically open the
        generated seed mask

    Returns
    -------
    numpy.ndarray[numpy.bool]
        image with lines that separate neighbouring watershed regions

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''
    smoothed = mh.gaussian_filter(img, 1).astype(img.dtype)
    t = mh.otsu(smoothed[mask])
    threshed = smoothed > t
    dist = mh.stretch(mh.distance(threshed))
    strel = ski.morphology.square(ksize)
    peaks = mh.morph.regmax(dist, Bc=strel)
    seeds = mh.label(peaks, Bc=strel)[0]
    watershed_regions = mh.cwatershed(np.invert(dist), seeds)
    watershed_regions[~mask] = 0
    # "subpixel" mode provides a valid skeleton, but it doubles the size of
    # the image -> watershed_regions.shape[i] is equal to 2 * lines.shape[i] - 1
    lines= ski.segmentation.find_boundaries(watershed_regions, mode='thick')
    outer_lines= ski.segmentation.find_boundaries(mask, mode='thick')
    lines[outer_lines] = 0
    lines = mh.thin(lines)
    return lines


def find_branch_points(skeleton):
    '''Finds branch points of a skeleton.

    Parameters
    ----------
    skeleton: numpy.ndarray[numpy.bool]
        array with skeleton lines

    Returns
    -------
    numpy.ndarray[numpy.int32]
        labeled branch points

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''
    # TODO: globals?
    # skeleton = skeleton.astype(int)
    x0  = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]])
    x1 = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])
    t0 = np.array([[0, 0, 0], [1, 1, 1], [0, 1, 0]])
    t1 = np.flipud(t0)
    t2 = t0.T
    t3 = np.fliplr(t2)
    t4 = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 0]])
    t5 = np.flipud(t4)
    t6 = np.fliplr(t4)
    t7 = np.fliplr(t5)
    y0 = np.array([[1, 0, 1], [0, 1, 0], [2, 1, 2]])
    y1 = np.flipud(y0)
    y2 = y0.T
    y3 = np.fliplr(y2)
    y4 = np.array([[0, 1, 2], [1, 1, 2], [2, 2, 1]])
    y5 = np.flipud(y4)
    y6 = np.fliplr(y4)
    y7 = np.fliplr(y5)
    strels = [
        x0, x1, t0, t1, t2, t3, t4, t5, t6, t7, y0, y1, y2, y3, y4, y5, y6, y7
    ]
    nodes = np.zeros(skeleton.shape)
    for s in strels:
        nodes += mh.morph.hitmiss(skeleton, s)
    return mh.label(nodes)[0]


def find_end_points(skeleton):
    '''Finds end points of a skeleton.

    Parameters
    ----------
    skeleton: numpy.ndarray[numpy.bool]
        array with skeleton lines

    Returns
    -------
    numpy.ndarray[numpy.int32]
        labeled end points

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''
    s1 = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 0]])
    s2 = np.fliplr(s1)
    s3 = np.flipud(s1)
    s4 = np.fliplr(np.flipud(s1))
    s5 = np.array([[1, 1, 0], [0, 1, 0], [0, 0, 0]])
    s6 = np.fliplr(s5)
    s7 = np.flipud(s5)
    s8 = np.fliplr(np.flipud(s5))
    s9 = np.array([[0, 0, 0], [1, 1, 0], [0, 0, 0]])
    s10 = np.fliplr(s9)
    s11 = np.array([[0, 0, 0], [0, 1, 0], [0, 1, 0]])
    s12 = np.flipud(s11)
    s13 = np.array([[1, 0, 0], [1, 1, 0], [0, 0, 0]])
    s14 = np.fliplr(s13)
    s15 = np.flipud(s13)
    s16 = np.fliplr(np.flipud(s13))
    strels = [
        s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15, s16
    ]
    nodes = np.zeros(skeleton.shape)
    for s in strels:
        nodes += mh.morph.hitmiss(skeleton, s)
    return mh.label(nodes)[0]


def get_line_segments(skeleton, branch_points):
    '''Gets all individual line segments of a `skeleton` separated at
    `branch_points`.

    Parameters
    ----------
    skeleton: numpy.ndarray[numpy.bool]
        line skeletons
    branch_points: numpy.ndarray[numpy.bool]
        branch points

    Returns
    -------
    numpy.ndarray[numpy.int32]
        labeled line segments

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''
    return mh.label((skeleton > 0) - (branch_points > 0))[0]


def map_nodes_to_edges(nodes, edges):
    '''Map nodes to connecting edges.

    Parameters
    ----------
    nodes: numpy.ndarray[numpy.int32]
        labeled end and branch points
    edges: numpy.ndarray[numpy.int32]
        labeled line segments

    Returns
    -------
    Tuple[Dict[int, Set[int]]]
        mappings of nodes and connecting edges
    '''
    node_ids = np.unique(nodes[nodes > 0])
    edge_ids = np.unique(edges[edges > 0])
    node_to_egdes_map = dict()
    edge_to_nodes_map = dict()
    for n in node_ids:
        node_index = mh.morph.dilate(nodes == n)
        node_to_egdes_map[n] = set(np.unique(edges[node_index])[1:])
    for e in edge_ids:
        # TODO: There seem to be nodes missing!
        edge_index = mh.morph.dilate(edges == e)
        connected_nodes = set(np.unique(nodes[edge_index])[1:])
        if len(connected_nodes) < 2:
            raise ValueError('Edge %d must connect two nodes.' % e)
        edge_to_nodes_map[e] = connected_nodes
    return (node_to_egdes_map, edge_to_nodes_map)


def build_graph(node_map, edge_map):
    '''Builds a graph.

    Parameters
    ----------
    node_map: Dict[int, Set[int]]
        mapping of nodes to connecting edges
    edge_map: Dict[int, Set[int]]
        mapping of edges to nodes

    Returns
    -------
    Dict[int, Set[int]]
        graph
    '''
    graph = collections.defaultdict(set)
    for n, edge_ids in node_map.iteritems():
        for e in edge_ids:
            graph[n].update(edge_map[e])
        graph[n].remove(n)
    return graph


def find_all_paths(graph, start, end, path=[]):
    '''Finds all paths in `graph` from given `start` to `end` node.

    Parameters
    ----------
    graph: Dict[int, List[int]]
        nodes and connected edges
    start: int
        start node
    end: int
        end node

    Returns
    -------
    List[List[int]]
        all paths
    '''
    path = path + [start]
    if start == end:
        return [path]
    if not graph.has_key(start):
        return []
    paths = []
    for node in graph[start]:
        if node not in path:
            newpaths = find_all_paths(graph, node, end, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def find_shortest_path(graph, start, end, path=[]):
    '''Finds shortest path in `graph` from given `start` to `end` node.

    Parameters
    ----------
    graph: Dict[int, List[int]]
        nodes and connected edges
    start: int
        start node
    end: int
        end node

    Returns
    -------
    List[int]
        shorted paths
    '''
    path = path + [start]
    if start == end:
        return path
    if not graph.has_key(start):
        return None
    shortest = None
    for node in graph[start]:
        if node not in path:
            newpath = find_shortest_path(graph, node, end, path)
            if newpath:
                if not shortest or len(newpath) < len(shortest):
                    shortest = newpath
    return shortest


def find_line_segments_along_path(path, node_map):
    segments = list()
    for i, n in enumerate(path):
        if i == len(path) - 1:
            break
        segments += [
            e for e in node_map[n] if e in node_map[path[i+1]]
        ]
    return segments


def get_individual_lines(labeled_skeleton, branch_points, end_points):
    lines = list()
    skel_ids = np.unique(labeled_skeleton[labeled_skeleton > 0])
    for i in skel_ids:
        skel = labeled_skeleton == i
        bpts = branch_points == i
        epts = end_points == i
        segments, n = mh.label(skel - pts)
        segment_ids = np.arange(n)
        for j in segment_ids:
            coords = np.array(np.where(segments == j)).T
            line = asLineString(coords)
        # NOTE: shapely works with x, y coordinates, we leave them
        # in y, x order to make indexing to facilitate indexing into
        # numpy arrays
        # coords = zip(*np.fliplr(coords))
        # line = MultiLineString(coords)
        lines.append(line)


def main(label_image, intensity_image):

    ksize_regions = 5
    ksize_lines = 10

    object_ids = np.unique(label_image[label_image > 0])

    cut_mask = np.zeros(label_image.shape, dtype=label_image.dtype)
    if len(object_ids) == 0:
        # If there are no objects to cut we can simply return an empty cut mask
        return cut_mask

    props = ski.measure.regionprops(label_image)
    for i, oid in enumerate(object_ids):
        obj_img = jtlib.utils.crop_image(label_image, props[i].bbox, pad=True)
        obj_img = obj_img == oid
        int_img = jtlib.utils.crop_image(intensity_image, props[i].bbox, pad=True)

        concave_region_points, n_concave_regions = find_concave_regions(
            obj_img, ksize_regions
        )
        concave_region_points = mh.label(concave_region_points)[0]
        concave_region_point_ids = np.unique(concave_region_points)[1:]
        if n_concave_regions < 2:
            # Cut requires at least two concave regions
            continue

        skeleton = find_watershed_lines(obj_img, int_img, ksize_lines)
        branch_points = find_branch_points(skeleton)
        end_points = find_end_points(skeleton)
        end_point_ids = np.unique(end_points)[1:]
        line_segments = get_line_segments(skeleton, branch_points)
        nodes, n_nodes = mh.label((branch_points + end_points) > 0)
        node_ids = np.unique(nodes)[1:]
        node_edge_map, edge_note_map = map_nodes_to_edges(nodes, line_segments)

        # Find the nodes that lie closest to concave regions.
        # These will be the start and end points of the cut lines
        concave_region_point_node_map = dict()
        for cid in concave_region_point_ids:
            cpt = np.array(np.where(concave_region_points == cid)).T[0, :]
            dists = dict()
            for eid in end_point_ids:
                ept = np.array(np.where(end_points == eid)).T[0, :]
                # We use end point id to retrieve the correct coordinate,
                # we want to track the point by node id
                nid = nodes[tuple(ept)]
                dists[nid] = np.linalg.norm(cpt - ept)

            min_dist = np.min(dists.values())
            concave_region_point_node_map.update({
                cid: nid for nid, d in dists.iteritems() if d == min_dist
            })

        # Build a graph, where end and branch points are nodes
        # and line segments are edges
        graph = build_graph(node_edge_map, edge_note_map)
        target_nodes = concave_region_point_node_map.values()
        # Find lines that connect start and end points (all combinations)
        lines = collections.defaultdict(list)
        for start, end in itertools.combinations(target_nodes, 2):
            # path = find_shortest_path(graph, start, end)
            paths = find_all_paths(graph, start, end)
            for p in paths:
                line_ids = find_line_segments_along_path(p, node_edge_map)
                # TODO: consider building shapely line sting
                line = np.zeros(line_segments.shape, bool)
                for lid in line_ids:
                    line[line_segments == lid] = 1
                for nid in p:
                    line[nodes == nid] = 1
                lines[(start, end)].append(line)

        # TODO: measure intensity along line

        # Padding introduces artifacts for tophat filter
        # TODO: opencv for speed?
        # k= np.ones((ksize_regions, ksize_regions))
        # bth_img = cv2.morphologyEx(mh.stretch(int_img), cv2.MORPH_BLACKHAT, k)
        bth_img = ski.morphology.black_tophat(int_img)
        wth_img = ski.morphology.white_tophat(int_img)
        ma_img, dist_img = ski.morphology.medial_axis(obj_img, return_distance=True)
        import ipdb; ipdb.set_trace()



        # concave_regions = label(current_preim_props)
        # num_concave = np.unique(concave_regions)
        # props_concave_region = np.zeros(num_concave)
        # pixelsconcave_regions = list(num_concave)

        # for j in num_concave:
        #     props_current_region = current_preim_props[concave_regions == j,:]
        #     normal_vectors = props_current_region[:,3:4]
        #     norm_curvature = props_current_region[:,9]
# #                props_concave_region[j] = np.max(norm_curvature)
# #                props_concave_region[j] = np.mean(norm_curvature)
        #     maxima_indices = (norm_curvature == np.max(norm_curvature))
            
        #     props_concave_region[j,3:4] = np.mean(
        #                                   normal_vectors[maxima_indices,:],1)
            
        #     props_concave_region[j,5:6] = np.mean(normal_vectors,1)
        #     first_maximum_index = maxima_indices(1)
        #     last_maximum_index = maxima_indices(-1)
        #     mean_maximum_index = np.round(
        #                       (last_maximum_index + first_maximum_index)/2)
            
        #     props_concave_region[j,7:8] = props_current_region[
        #                                     mean_maximum_index,1:2]
                                            
        #     props_concave_region[j,9:10] = props_current_region[np.round(
        #                                   (np.shape(
        #                                   props_current_region)[0]+1)/2),1:2]
            
        #     props_concave_region[j,11] = np.sum(norm_curvature)
        #     props_concave_region[j,12] = len(norm_curvature)/np.sum(
        #                                                     norm_curvature)
        #     props_concave_region[j,13] = j
        #     pixelsconcave_regions[j] = props_current_region[:,1:2]
            
        # if np.shape(props_concave_region)[0] > num_region_threshold:
        #     raise ValueError(
        #     "object skipped because it has too many concave regions \\n")
        #     continue
        
        # qualifying_regions_mask = (props_concave_region[:,11] >= min_eqiv_angle) \
        #                 and (props_concave_region[:,12] <= max_eqiv_radius)
        
        # selected_regions = props_concave_region[qualifying_regions_mask,:]
        # cut_coord_list = selected_regions[:,[7,8]]
        # region_index = (np.arange(len(cut_coord_list))).T
        # if np.shape(cut_coord_list)[0] > 1:
        #     rcut = cut_coord_list[:,1] + 1 - north1[i]
        #     ccut = cut_coord_list[:,2] + 1 - west1[i]
        #     minicut_coord_list = np.array([rcut,ccut])
        #     immini = label_image[north1[i]:south1[i],west1[i]:east1[i]]
        #     imbwmini = immini == i
        #     imintmini = intensity_image[north1[i]:south1[i],west1[i]:east1[i]]
        #     imintmini[~imbwmini] = 0
        #     padsize = np.array([1,1])
        #     padbw = np.pad(imbwmini,padsize)
        #     padint = np.pad(imintmini,padsize)
        #     padws = cv2.watershed(PIL.imageops.invert(padint))
        #     padws[np.logical_not(padbw)] = 0
        #     imcurrentprelines = np.zeros(np.shape(padint))
        #     imcurrentprelines[~padws] = padbw[~padws]
        #     imcurrentprelines[~padbw] = 0
        #     imcurrentprelines2 = imcurrentprelines
        #     imcurrentprelines2[~padbw] = 5
            
        #     f = np.array([[0,1,0],[1,0,1],[0,1,0]])
        #     imcurrentlinesandnodes = sp.misc.imfilter(imcurrentprelines2,f)
        #     imcurrentlinesandnodes[~imcurrentprelines2] = 0
        #     imcurrentlinesandnodes[~padbw] = 0
        #     imcurrentlines = label(imcurrentlinesandnodes < 3 
        #                      and imcurrentlinesandnodes > 0,4)
        #     lineprops = regionprops(imcurrentlines)
        #     lineareas = lineprops.area
        #     lineids = np.unique(imcurrentlines[:])
        #     lineids[lineids == 0] = []
        #     imcurrentnodes = label(imcurrentlinesandnodes > 2,4)
        #     nodesprops = regionprops(imcurrentnodes)
        #     nodescentroids = nodesprops.centroid
        #     nodesids = np.unique(imcurrentnodes[:])
        #     nodesids = nodesids[2:-1].T
        #     f = [[[0,1,0],[0,0,0],[0,0,0]],[[0,0,0],[1,0,0],[0,0,0]], \
        #          [[0,0,0],[0,0,1],[0,0,0]],[[0,0,0],[0,0,0],[0,1,0]]]
                 
        #     displacedlines = sp.misc.imfilter(imcurrentlines,f)
        #     displacedlines = np.concatenate(3,displacedlines[:])
        #     nodeType = np.zeros(np.shape(nodesids))
        #     matnodeslines = np.zeros(len(nodesids),len(lineareas))
        #     for inode in len(nodesids):
        #         tmpid = nodesids[inode]
        #         tmpix = imcurrentnodes == tmpid
        #         temptype = np.unique(imcurrentlinesandnodes[tmpix])
        #         nodeType[inode] = np.max(temptype) > 5
        #         tmpix = np.tile(tmpix,(4,1))
        #         templineids = np.unique(displacedlines[tmpix])
        #         templineids[templineids == 0] = []
        #         matnodeslines[inode,templineids.T] = templineids.T
        #     matnodesnodes = np.zeros(len(nodesids))
        #     matnodesnodeslabel = np.zeros(len(nodesids))
        #     for inode in len(nodesids):
        #         tmplines = np.unique(matnodeslines[inode,:])
        #         tmplines[tmplines == 0] = []
        #         for l in tmplines.reshape(-1):
        #             tmpnodes = matnodeslines[:,l] > 0
        #             matnodesnodes[inode,tmpnodes] = lineareas[l]
        #             matnodesnodeslabel[inode,tmpnodes] = l
                    
        #     matnodesnodes[np.ravel_multi_index((nodesids,nodesids), 
        #                 dims=(len(nodesids),len(nodesids)), order='C')] = 0
        #     matnodesnodeslabel[np.ravel_multi_index((nodesids,nodesids), 
        #                 dims=(len(nodesids),len(nodesids)), order='C')] = 0
# #                matnodesnodeslabel[np.ravel_multi_index(
# #                    [len(nodesids),len(nodesids)],(nodesids,nodesids))] = 0
            
        #     node_to_test = nodesids[(nodeType>0)]
            
        #     if kwargs['debug']:
        #         i,j1 = np.transpose(
        #                         filter(lambda a: a !=  0, imcurrentlines))
        #         #i,j1 = np.transpose(np.nonzero(imcurrentlines))
        #         plt.imshow(padint)
        #         plt.title(['object #'+ i])
        #         plt.hold(True)
        #         plt.scatter(j1,i,150)
        #         plt.scatter(nodescentroids[node_to_test,1],
        #                     nodescentroids[node_to_test,2],2000)
        #         plt.hold(False)
                
        #     potentialnodescoordinates = nodescentroids[node_to_test,:]
        #     potentialnodescoordinates = np.round(potentialnodescoordinates)
        #     nodecoordlist = np.zeros(np.shape(potentialnodescoordinates))
        #     if len(potentialnodescoordinates) > 0  \
        #         and len(minicut_coord_list) >0:
                    
        #         alllines = list()
        #         nodecoordlist[:,1] = potentialnodescoordinates[:,2]
        #         nodecoordlist[:,2] = potentialnodescoordinates[:,1]
        #         __,closestnodesindex = np.linalg.norm(
        #                                nodecoordlist,minicut_coord_list)
        #         closestnodesindex = np.unique(closestnodesindex[:])
                
        #         if kwargs['debug']:
        #             plt.imshow(padint)
        #             plt.title(['object #'+ i])
        #             plt.hold(True)
        #             plt.scatter(
        #             minicut_coord_list[:,2],minicut_coord_list[:,1],2000)
        #             plt.hold(False)
        #             selectednodecoordlist = nodecoordlist[closestnodesindex,:]
        #             plt.imshow(padint)
        #             plt.title(['object #'+ i])
        #             plt.hold(True)
        #             plt.scatter(
        #             selectednodecoordlist[:,2],
        #             selectednodecoordlist[:,1],2000)
        #             plt.hold(False)
                    
        #         if len(closestnodesindex) > 0:
        #             closestnodesids = node_to_test[closestnodesindex]
        #             nodeixs = np.tile(closestnodesids,[len(closestnodesids),1])
        #             nodeixt = np.tile(closestnodesids,[1,len(closestnodesids)])
        #             nodeixs = nodeixs[:]
        #             nodeixt = nodeixt[:]
                    
        #             dist,path = jtlib.dijkstra(matnodesnodes > 0,
        #                                        matnodesnodes,
        #                                        closestnodesids,
        #                                        closestnodesids,nargout=2)
                    
        #             dist = dist[:].T
        #             dist = filter(lambda a: a != 0, dist) and \
        #                    filter(lambda a: a != np.inf, dist)
                           
        #             quantile_distance = np.quantile(dist)
        #             thrix = filter(lambda a: a != 0, dist)  and \
        #                     filter(lambda a: a < quantile_distance, dist)
                            
        #             nodeixs2 = nodeixs[thrix]
        #             nodeixt2 = nodeixt[thrix]
        #             nodescoordlist = nodescentroids[nodeixs2,:]
        #             nodescoordlist = np.round(nodescoordlist)
        #             nodetcoordlist = nodescentroids[nodeixt2,:]
        #             nodetcoordlist = np.round(nodetcoordlist)
        #             __,closestcutpointssindex = np.linalg.norm(
        #                                         minicut_coord_list,
        #                                         np.fliplr(nodescoordlist))
                    
        #             closestcutpointssindex = closestcutpointssindex[:]
        #             __,closestcutpointstindex = np.linalg.norm(
        #                                         minicut_coord_list,
        #                                         np.fliplr(nodetcoordlist))
        #             closestcutpointstindex = closestcutpointstindex[:]
        #             alllines = list()
        #             for n in len(nodeixt2):
        #                 tmppath = path[closestnodesids == nodeixs2[n], 
        #                             closestnodesids == nodeixt2[n]]
                                    
        #                 tmpimage = np.zeros(np.shape(imcurrentnodes))
        #                 t1 = ismember.ismember(imcurrentnodes,tmppath)
        #                 tmpimage[t1] = 1
        #                 for j in len(tmppath):
        #                     tmpimage[imcurrentlines == 
        #                                     matnodesnodeslabel[
        #                                     tmppath[j],tmppath[j+1]]] = 1
        #                 tmpsegmentation = padbw
        #                 tmpsegmentation[tmpimage > 0] = 0
        #                 tmpsubsegmentation = label(tmpsegmentation > 0)
        #                 tmpnumobjects = np.unique(tmpsubsegmentation)
                        
        #                 tmpsubareas = list(tmpsubsegmentation.pixelidxlist)
        #                 if tmpnumobjects == 2 and np.min(
        #                                     tmpsubareas) > objsize_thres:
                            
        #                     [tmpsubareas, tmpsubsolidity, tmpsub_formfactor] = \
        #                     calculate_object_features(tmpsegmentation)
                            
        #                     alllines[n].areasobj = tmpsubareas
        #                     alllines[n].solobj = tmpsubsolidity
        #                     alllines[n].formobj = tmpsub_formfactor
        #                     alllines[n].lineimage = tmpimage
        #                     alllines[n].segmimage = tmpsegmentation
        #                     tmpintimage = tmpimage > 0
        #                     tmpmaxint = np.max(padint[tmpintimage])
        #                     tmpmeanint = np.mean(padint[tmpintimage])
        #                     tmpstdint = np.std(padint[tmpintimage])
        #                     tmpquantint = np.quantile(padint[tmpintimage],0.75)
        #                     tmplength = np.sum(tmpintimage[:])
        #                     alllines[n].maxint = tmpmaxint
        #                     alllines[n].meanint = tmpmeanint
        #                     alllines[n].quantint = tmpquantint
        #                     alllines[n].stdint = tmpstdint
        #                     alllines[n].length = tmplength
        #                     tmpcentroid1 = np.round(
        #                             nodescentroids[closestnodesids
        #                             [closestnodesids == nodeixs2[n]],:])
                            
        #                     tmpcentroid2 = np.round(
        #                             nodescentroids[closestnodesids
        #                             [closestnodesids == nodeixt2[n]],:])
                            
        #                     temp1 = (tmpcentroid1[2] - tmpcentroid2[2])
        #                     temp2 = (tmpcentroid1[1] - tmpcentroid2[1])
                            
        #                     m =  temp1 / temp2
                            
        #                     x = list(range(np.min(
        #                         [tmpcentroid1[1],tmpcentroid2[1]]),np.max(
        #                         [tmpcentroid1[1],tmpcentroid2[1]])))
        #                     if m != -np.inf and m != np.inf and ~np.isnan(m):
        #                         y = list(range(np.min(
        #                         [tmpcentroid1[2],tmpcentroid2[2]]),
        #                         np.max([tmpcentroid1[2],tmpcentroid2[2]])))
                                
        #                         c = tmpcentroid1[2] - m * tmpcentroid1[1]
        #                         py = np.round(m.dot(x) + c)
        #                         px = np.round((y - c) / m)
        #                         if np.max(
        #                             np.shape(tmpimage)[0])>np.max(
        #                             [y,py]) and np.max(
        #                             np.shape(tmpimage)[1]) > np.max([px,x]):
                                        
        #                             straigtlineix = np.ravel_multi_index(
        #                                     np.shape(tmpimage),[y,py],[px,x])
        #                         else:
        #                             straigtlineix = np.nan
        #                     else:
        #                         straigtlineix = np.nan
        #                     tmprim = tmpimage
        #                     tmprim[straigtlineix[not np.isnan(
        #                                             straigtlineix)]] = 1
        #                     tmprim = ndi.binary_fill_holes(tmprim)
        #                     tmpRatio = np.sum(tmprim[:]) / len(np.unique(
        #                                                 straigtlineix))
        #                     alllines[n].straightness = tmpRatio
        #                     currentsourcenode = region_index[
        #                                         closestcutpointssindex[n]]
        #                     currentTargetnode = region_index[
        #                                         closestcutpointstindex[n]]
                                                
        #                     regiona = current_preim_props[concave_regions 
        #                             == selected_regions
        #                             [currentsourcenode,13],[1,2,3,4]]
                                    
        #                     regionb = current_preim_props[concave_regions 
        #                             == selected_regions
        #                             [currentTargetnode,13],[1,2,3,4]]
        #                     allangles = np.zeros(np.shape(regiona)[0]
        #                                             ,np.shape(regionb)[0])
        #                     for l in np.shape(regiona)[0]:
        #                         for m in np.shape(regionb)[0]:
        #                             connectingVectorab = regionb[m,1:2] - \
        #                                                     regiona[l,1:2]
                                    
        #                             t1 = connectingVectorab/np.linalg.norm(  
        #                                                  connectingVectorab)
        #                             connectingVectorab = t1
                                                        
        #                             connectingVectorba = -connectingVectorab
        #                             angledeviationa = math.acos(math.dot(
        #                                               regiona[l,3:4],
        #                                               connectingVectorab))
        #                             angledeviationb = math.acos(math.dot(
        #                                               regionb[m,3:4],
        #                                               connectingVectorba))
                                    
        #                             t1 = (angledeviationa+angledeviationb)/2
# #                                        meanangledeviation = t1
        #                             allangles[l,m] = np.pi - t1
        #                     allangles = np.real(allangles)
        #                     tmpangle = np.max(allangles[:])
        #                     alllines[n].angle = tmpangle
        #     else:
        #         alllines = list()
                
        #     if len(alllines[:]) > 0:
        #         alllines = filter(None, alllines) 
        #         if len(alllines) == 1:
        #             bestlinesindex = 1
        #         else:
        #             if kwargs['debug']:
        #                 alllinesimage = np.zeros(np.shape(padint))
        #                 for d in len(alllines):
        #                     alllinesimage[alllines[d].lineimage > 0] = 1
        #                 i,j1 = np.transpose(filter(
        #                                 lambda a: a != 0, alllinesimage))
        #                 #i,j1 = np.transpose(np.nonzero(alllinesimage))
        #                 plt.imshow(padint)
        #                 plt.title(['object #'+ i])
        #                 plt.hold(True)
        #                 plt.scatter(j1,i,150)
        #                 plt.scatter(
        #                     selectednodecoordlist[:,2],
        #                     selectednodecoordlist[:,1],3000)
        #                 plt.hold(False)
        #             optfunc = lambda a,b,c,d,e,f,g,h: \
        #                 a - 2 * b - c - d - e + 2 * f - g - 2 * h
        #             linemaxint = alllines.maxint
        #             linemeanint = alllines.meanint
        #             linestraight = alllines.straightness
        #             lineangle = alllines.angle
        #             linelength = alllines.length
        #             linequantint = alllines.quantint
        #             solobjs = alllines.solobj
        #             formobjs = alllines.formobj
        #             smallindex = np.min((alllines.areasobj),[],2,nargout=2)
        #             solobj = np.zeros(np.shape(solobjs)[0])
        #             formobj = np.zeros(np.shape(formobjs)[0])
        #             for k in np.shape(solobjs)[0]:
        #                 solobj[k,1] = solobjs[k,smallindex[k]]
        #                 formobj[k,1] = formobjs[k,smallindex[k]]
                        
        #             bestlines = optfunc[solobj,formobj,linemeanint.dot(100),
        #                             linemaxint.dot(10),linequantint.dot(10),
        #                             lineangle,linestraight/10,linelength/10]
                                        
        #             bestlinesindex = sorted(bestlines, reverse=True)
        #         if kwargs['debug']:
        #             bestlineimage = np.zeros(np.shape(padint))
        #             bestlineimage[alllines[
        #                             bestlinesindex[1]].lineimage > 0] = 1
        #             i,j1 = np.transpose(
        #                             filter(lambda a: a != 0, bestlineimage))
        #             #i,j1 = np.transpose(np.nonzero(bestlineimage))
        #             plt.imshow(padint)
        #             plt.title(['object #'+ i])
        #             plt.hold(True)
        #             plt.scatter(j1,i,150)
        #         if len(bestlinesindex) > len(alllines):
        #             raise ValueError(
        #                     "Failed to find a more optimal cut for object")
        #         else:
        #             imbestline = alllines[bestlinesindex[1]].lineimage
        #             if np.max(imbestline[:]) > 0:
        #                 imbestline = imbestline[(padsize[1]+1):
        #                             (-1 - padsize[1]),
        #                             (padsize[2] + 1):(-1 - padsize[2])]
                                    
        #                 rmini,cmini = np.transpose(
        #                                 filter(lambda a: a != 0, imbwmini))
        #                 #rmini,cmini = np.transpose(np.nonzero(imbwmini))
        #                 wmini = np.ravel_multi_index(
        #                         np.shape(imbwmini),(rmini,cmini))
        #                 r = rmini - 1 + north1[i]
        #                 c = cmini - 1 + west1[i]
        #                 w = np.ravel_multi_index(np.shape(cut_mask),(r,c))
        #                 cut_mask[w] = imbestline[wmini]

    # cut_mask = cut_mask > 0
    # kernel = np.ones((3,3),np.uint8)
    # opening = cv2.morphology(cut_mask,cv2.morph_open,kernel, iterations = 2)
    # cut_mask = cv2.dilate(opening,kernel,iterations=3)
    # return cut_mask
