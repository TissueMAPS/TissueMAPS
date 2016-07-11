'''Jterator module for separation of clumps in a binary image,
where a `clump` is a connected component with certain size and shape.
'''
import numpy as np
import cv2
import heapq
import pandas as pd
import itertools
import collections
import mahotas as mh
import skimage.morphology
import logging
import jtlib.utils


logger = logging.getLogger(__name__)
PAD = 1


def find_concave_regions(mask, max_dist):
    '''Finds convace regions along the contour of `mask`.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        mask image
    max_dist: int
        maximally tolerated distance between concave point on object contour
        and the convex hull

    Note
    ----
    Fast implementation in C++ using `OpenCV library <http://opencv.org/>`_.
    '''
    contour_img = np.zeros(mask.shape, dtype=np.uint8)
    contour_img[mask] = 255
    contour_img, contours, _ = cv2.findContours(
        contour_img, mode=cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_SIMPLE
    )
    concave_img = np.zeros(mask.shape, dtype=np.bool)
    for cnt in contours:
        hull = cv2.convexHull(cnt, returnPoints=False)
        defects = cv2.convexityDefects(cnt, hull)
        if defects is not None:
            defect_pts = np.array([
                cnt[defects[j, 0][2]][0]
                for j in xrange(defects.shape[0])
                if defects[j, 0][3]/float(256) > max_dist
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
        size of the kernel that's used to detect regional maxima in `img`
        within `mask`

    Returns
    -------
    numpy.ndarray[numpy.bool]
        image with lines that separate neighbouring watershed regions

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''

    if ksize < 2:
        ksize = 2
    se = skimage.morphology.square(ksize)
    peaks = mh.morph.regmax(img, Bc=se)
    seeds = mh.label(peaks)[0]
    watershed_regions = mh.cwatershed(np.invert(img), seeds)
    watershed_regions[~mask] = 0
    lines = mh.labeled.borders(watershed_regions)
    outer_lines = mh.labeled.borders(mask)
    lines[outer_lines] = 0
    lines = mh.thin(lines)
    labeled_lines = mh.label(lines)[0]
    sizes = mh.labeled.labeled_size(labeled_lines)
    too_small = np.where(sizes < 10)
    lines = mh.labeled.remove_regions(labeled_lines, too_small) > 0
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


def find_border_points(skeleton, mask):
    '''Finds points of `skeleton` that intersect with the border (contour)
    of an object defined by `mask`.

    Parameters
    ----------
    skeleton: numpy.ndarray[numpy.bool]
        image of skeleton lines
    mask: numpy.ndarray[numpy.bool]
        mask image

    Returns
    -------
    numpy.ndarray[numpy.int32]
        labeled border points

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''
    points = (
        skeleton +
        mh.morph.erode(mask)*2 +
        (skeleton != mh.morph.erode(mh.morph.erode(mask)))*3
    ) == 6
    return mh.label(points)[0]


def find_end_points(skeleton):
    '''Finds end points of a skeleton.

    Parameters
    ----------
    skeleton: numpy.ndarray[numpy.bool]
        image of skeleton lines

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


def get_line_segments(skeleton, branch_points, end_points):
    '''Gets all individual line segments of a `skeleton` separated at
    `branch_points`.

    Parameters
    ----------
    skeleton: numpy.ndarray[numpy.bool]
        image of skeleton
    branch_points: numpy.ndarray[numpy.bool]
        image of branch points
    end_points: numpy.ndarray[numpy.bool]
        image of end points

    Returns
    -------
    numpy.ndarray[numpy.int32]
        labeled line segments

    Note
    ----
    Fast implementation in C++ using
    `mahotas library <http://mahotas.readthedocs.io/en/latest/>`_.
    '''
    segments = mh.label((skeleton > 0) - (branch_points > 0))[0]
    sizes = mh.labeled.labeled_size(segments)
    # Cutting the skeleton into segments may result in small spurs that are
    # not connected to two nodes. We remove them here.
    too_small = np.where(sizes < 10)[0]
    se = np.ones((3, 3), bool)  # 8-connected!
    if too_small.size > 0:
        check_points = mh.label((branch_points + end_points) > 0, Bc=se)[0]
        remove = list()
        for s in too_small:
            index = mh.morph.dilate(segments == s)
            if len(np.unique(check_points[index])) < 3:
                remove.append(s)
        remove = np.array(remove)
    else:
        remove = too_small
    if remove.size > 0:
        segments = mh.labeled.remove_regions(segments, remove) > 0
    return mh.label(segments > 0)[0]


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
    se = np.ones((3, 3), bool)  # 8-connected!
    for n in node_ids:
        node_index = mh.morph.dilate(nodes == n, Bc=se)
        node_to_egdes_map[n] = set(np.unique(edges[node_index])[1:])
    for e in edge_ids:
        edge_index = mh.morph.dilate(edges == e, Bc=se)
        connected_nodes = set(np.unique(nodes[edge_index])[1:])
        if len(connected_nodes) < 2:
            # Sometimes there are small spurs that are only connected to
            # a single node. We ignore them.
            raise ValueError('Edge %d must connect two nodes.' % e)
        edge_to_nodes_map[e] = connected_nodes
    return (node_to_egdes_map, edge_to_nodes_map)


def build_graph(edges, node_map, edge_map):
    '''Builds a graph.

    Parameters
    ----------
    edges: numpy.ndarray[numpy.int32]
        labeled line segments
    node_map: Dict[int, Set[int]]
        mapping of nodes to connecting edges
    edge_map: Dict[int, Set[int]]
        mapping of edges to nodes

    Returns
    -------
    Dict[int, Dict[int]]
        graph, i.e. mapping of parent nodes to child nodes
    '''
    graph = dict()
    for n, edge_ids in node_map.iteritems():
        graph[n] = dict()
        for e in edge_ids:
            for nn in edge_map[e]:
                if nn == n:
                    continue
                graph[n].update({
                    nn: np.sum(edges[edges == e])
                })
    return graph


def find_shortest_path(graph, start, end):
    '''Finds shortest path between `start` and `end` node in `graph` using
    `Dijkstra's algorithm <https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm>`_.

    Parameters
    ----------
    graph: Dict[int, Dict[int]]
        mapping of parent nodes to child nodes
    start: int
        start node
    end: int
        end node

    Returns
    -------
    List[int]
        sequence of nodes along the shortest path

    See also
    --------
    :py:func:`jtmodules.separate_clumps.build_graph`
    '''
    queue = [(0, start, [])]
    been_there = set()
    while True:
        try:
            (distance, v, path) = heapq.heappop(queue)
        except IndexError:
            # We end up here when no line can be found in graph that connects
            # start and end nodes.
            logger.debug('incomplete line: {0}'.format(path))
            return []
        except:
            raise
        if v not in been_there:
            path = path + [v]
            been_there.add(v)
            if v == end:
                return path
            for (next, d) in graph[v].iteritems():
                heapq.heappush(queue, (distance + d, next, path))


def find_line_segments_along_path(path, node_map):
    '''Finds the line segments connecting nodes lying on `path`.

    Parameters
    ----------
    path: List[int]
        sequence of nodes in a graph
    node_map: Dict[int, Set[int]]
        mapping of nodes to lines connected to the nodes

    Returns
    -------
    List[int]
        sequence of line segments that connect nodes in `path`
    '''
    segments = list()
    for i, n in enumerate(path):
        if i == len(path) - 1:
            break
        segments += [
            e for e in node_map[n] if e in node_map[path[i+1]]
        ]
    return segments


def build_lines_from_segments(line_segments, nodes, graph, end_nodes, node_map):
    '''Builds lines by combining `line_segments` that connect pairs of
    `target_nodes` along all possible paths in `graph`.

    Parameters
    ----------
    line_segments: numpy.ndarray[numpy.int32]
        labeled image with line segments
    nodes: numpy.ndarray[numpy.int32]
        labeled image with nodes
    graph: Dict[int, Set[int]]
        mapping of parent nodes to child nodes
    end_nodes: List[Tuple[int]]
        end nodes of the `path` that should be connected
    node_map: Dict[int, Set[int]]
        mapping of nodes to connecting lines

    Returns
    -------
    Dict[Tuple[int], numpy.ndarray[numpy.bool]]
        shortest line connecting each pair of `end_nodes` provided a separate
        mask image for each line
    '''
    # Find lines that connect start and end points (all combinations)
    lines = dict()
    for start, end in itertools.combinations(set(end_nodes), 2):
        p = find_shortest_path(graph, start, end)
        line_ids = find_line_segments_along_path(p, node_map)
        line = np.zeros(line_segments.shape, bool)
        for lid in line_ids:
            line[line_segments == lid] = True
        for nid in p:
            line[nodes == nid] = True
        # Shapely line approach?
        # coords = np.array(np.where(line)).T
        # line = shapely.geometry.asLineString(coords)
        if np.count_nonzero(line) == 0:
            continue
        # We need to dilate the line a bit to ensure that it will actually
        # cut the entire object.
        lines[(start, end)] = mh.morph.dilate(line)
    return lines


def find_nodes_closest_to_concave_regions(concave_region_points, end_points, nodes):
    '''Finds end points within shortest distance to each concave region.

    Parameters
    ----------
    concave_region_points: numpy.ndarray[numpy.int32]
        labeled points marking concave regions on the object contour
    end_points: numpy.ndarray[numpy.int32]
        labeled points marking intersection points between lines and the
        object contour
    nodes: numpy.ndarray[numpy.int32]
        all labeled points

    Returns
    -------
    Dict[int, int]
        mapping of concave region points to closest end points
    '''
    concave_region_point_node_map = dict()
    concave_region_point_ids = np.unique(concave_region_points)[1:]
    end_point_ids = np.unique(end_points)[1:]
    for cid in concave_region_point_ids:
        cpt = np.array(np.where(concave_region_points == cid)).T[0, :]
        dists = dict()
        for eid in end_point_ids:
            ept = np.array(np.where(end_points == eid)).T[0, :]
            # We use end point id to retrieve the correct coordinate,
            # we want to track the point by node id
            nid = nodes[tuple(ept)]
            dists[nid] = np.linalg.norm(cpt - ept)
        if not dists:
            return dict()
        min_dist = np.min(dists.values())
        concave_region_point_node_map.update({
            cid: nid for nid, d in dists.iteritems() if d == min_dist
        })
    return concave_region_point_node_map


def calc_area_shape_features(mask):
    '''Calcuates `area` and shape features `form factor` and `solidity`
    for the given object.

    Parameters
    ----------
    mask: numpy.ndarray[numpy.bool]
        bounding box image representing the object

    Returns
    -------
    numpy.ndarray[numpy.float64]
        area, form factor and solidity
    '''
    mask = mask > 0
    area = np.float64(np.count_nonzero(mask))
    perimeter = mh.labeled.perimeter(mask)
    form_factor = (4.0 * np.pi * area) / (perimeter**2)
    convex_hull = mh.polygon.fill_convexhull(mask)
    area_convex_hull = np.count_nonzero(convex_hull)
    solidity = area / area_convex_hull
    # eccentricity = mh.features.eccentricity(mask)
    # roundness = mh.features.roundness(mask)
    # major_axis, minor_axis = mh.features.ellipse_axes(mask)
    # elongation = (major_axis - minor_axis) / major_axis
    return np.array([area, form_factor, solidity])


# def calc_complex_shape_features(mask):
#     '''Calculates Zernike moments that describe the shape of the object
#     in mask.

#     Parameters
#     ----------
#     mask: numpy.ndarray[numpy.bool]
#         bounding box image containing the object where ``True`` is foreground
#         and ``False`` background

#     Returns
#     -------
#     numpy.ndarray[numpy.float64]
#         shape features
#     '''
#     radius = 100
#     mask_rs = mh.imresize(mask, (radius, radius))
#     return mh.features.zernike_moments(mask, degree= 12, radius=radius/2)


def create_area_shape_feature_images(label_image):
    '''Creates label images, where each object is color coded according to
    area/shape features.

    Parameters
    ----------
    label_image: numpy.ndarray[numpy.int32]
        labeled image

    Returns
    -------
    Tuple[numpy.ndarray[numpy.float64]]
        heatmap images for each feature
    '''
    label_image = mh.label(label_image > 0)[0]
    bboxes = mh.labeled.bbox(label_image)
    object_ids = np.unique(label_image)[1:]
    images = [np.zeros(label_image.shape, np.float64) for x in range(3)]
    # TODO: might be faster by mapping the image through a lookup table
    for i in object_ids:
        mask = jtlib.utils.extract_bbox_image(label_image, bboxes[i], pad=PAD)
        mask = mask == i
        shape_features = calc_area_shape_features(mask)
        for j, f in enumerate(shape_features):
            images[j][label_image == i] = f
    return tuple(images)


def main(input_mask, input_image, min_area, max_area,
        min_cut_area, max_cut_intensity, max_form_factor, max_solidity,
        region_sensitivity, line_sensitivity, cutting_passes, plot=False):
    '''Detects clumps in `input_mask` and cuts them along watershed lines
    connecting two points falling into concave regions on their contour.

    Parameters
    ----------
    input_mask: numpy.ndarray[numpy.bool]
        image with potential clumps
    input_image: numpy.ndarray[numpy.unit16 or numpy.uint8]
        image used for detection of watershed lines
    min_area: int
        minimal area an object must have to be considered a clump
    max_area: int
        maximal area an object must have to be considered a clump
    min_cut_area: int
        minimal area a cut object can have
        (useful to limit size of cut objects)
    max_cut_intensity: int
        percentile for calculation of a intensity cutoff value
    max_solidity: float
        maximal solidity an object must have to be considerd a clump
    max_form_factor: float
        maximal form factor an object must have to be considerd a clump
    region_sensitivity: int
        sensitivity of detecting concave regions along the contour of clumps
        (distance between the farthest contour point and the convex hull)
    line_sensitivity: int
        sensitivity of detecting potential cut lines within clumps
        (size of the kernel that's used to morphologically open the mask of
        regional intensity peaks, which are used as seeds for the watershed
        transform)
    cutting_passes: int
        number of cutting cycles to separate clumps that consist of more than
        two subobjects
    plot: bool, optional
        whether a plot should be generated

    Returns
    -------
    Dict[str, numpy.ndarray[numpy.bool] or str]
        * "output_mask": image with cut clumped objects
        * "figure": JSON figure representation
    '''

    # TODO: test modes
    kernel = np.ones((100, 100))
    blackhat_image = cv2.morphologyEx(
        mh.stretch(input_image), cv2.MORPH_BLACKHAT, kernel
    )
    output_mask = input_mask.copy()
    cut_mask = np.zeros(output_mask.shape, bool)
    clumps_mask = np.zeros(output_mask.shape, bool)
    intensity_cutoff = int(np.percentile(
        input_image[input_mask], max_cut_intensity)
    )
    for n in range(cutting_passes):
        logger.info('cutting pass #%d', n+1)
        label_image = mh.label(output_mask)[0]
        object_ids = np.unique(label_image[label_image > 0])
        if len(object_ids) == 0:
            logger.debug('no objects')
            continue

        bboxes = mh.labeled.bbox(label_image)
        for oid in object_ids:
            logger.debug('process object #%d', oid)
            mask = jtlib.utils.extract_bbox_image(
                label_image, bboxes[oid], pad=PAD
            )
            mask = mask == oid
            img = jtlib.utils.extract_bbox_image(
                input_image, bboxes[oid], pad=PAD
            )
            bhat = jtlib.utils.extract_bbox_image(
                blackhat_image, bboxes[oid], pad=PAD
            )

            area, form_factor, solidity = calc_area_shape_features(mask)
            if area < min_area or area > max_area:
                logger.debug('not a clump - outside area range')
                continue
            if form_factor > max_form_factor:
                logger.debug('not a clump - above form factor threshold')
                continue
            if solidity > max_solidity:
                logger.debug('not a clump - above solidity threshold')
                continue

            y, x = np.where(mask)
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD
            y += y_offset
            x += x_offset
            clumps_mask[y, x] = True

            concave_region_points, n_concave_regions = find_concave_regions(mask, region_sensitivity)
            concave_region_points = mh.label(concave_region_points)[0]
            concave_region_point_ids = np.unique(concave_region_points)[1:]
            if n_concave_regions < 2:
                logger.debug('no cut - not enough concave regions')
                continue

            skeleton = find_watershed_lines(mask, img, line_sensitivity)
            branch_points = find_branch_points(skeleton)
            end_points = find_border_points(skeleton, mask)
            end_points += find_end_points(skeleton)
            # Re-label 8-connected to ensure that neighboring end points get
            # assigned the same label
            se = np.ones((3, 3), bool)  # 8-connected
            end_points = mh.label(end_points > 0, Bc=se)[0]
            end_point_ids = np.unique(end_points)[1:]
            line_segments = get_line_segments(skeleton, branch_points, end_points)
            node_points, n_nodes = mh.label((branch_points + end_points) > 0, Bc=se)
            node_ids = np.unique(node_points)[1:]
            if n_nodes == 0:
                logger.debug(
                    'no cut - no watershed lines connceting concave regions'
                )
                continue

            # Find the nodes that lie closest to concave regions.
            # These will be the start and end points of the cut lines
            node_edge_map, edge_note_map = map_nodes_to_edges(
                node_points, line_segments
            )
            # TODO: limit distance to prevent ending up outside of concave region
            concave_region_point_node_map = find_nodes_closest_to_concave_regions(
                concave_region_points, end_points, node_points
            )

            # Build a graph, where end and branch points are nodes
            # and line segments are the edges that connect nodes
            graph = build_graph(line_segments, node_edge_map, edge_note_map)
            target_nodes = concave_region_point_node_map.values()

            # Build all lines that connect nodes in the graph
            lines = build_lines_from_segments(
                line_segments, node_points, graph, target_nodes, node_edge_map
            )
            if len(lines) == 0:
                logger.debug(
                    'no cut - no watershed lines found between concave regions'
                )
                continue

            features = list()
            for (start, end), line in lines.iteritems():
                test_cut_mask = mask.copy()
                test_cut_mask[line] = False
                test_cut_mask = mh.morph.open(test_cut_mask)
                subobjects, n_subobjects = mh.label(test_cut_mask)
                sizes = mh.labeled.labeled_size(subobjects)
                smaller_id = np.where(sizes == np.min(sizes))[0]
                smaller_object = subobjects == smaller_id
                area, form_factor, solidity = calc_area_shape_features(smaller_object)
                intensity = img[line]
                blackness = bhat[line]
                start_coord = np.array(np.where(node_points == start)).T[0, :]
                end_coord = np.array(np.where(node_points == end)).T[0, :]
                totally_straight = np.linalg.norm(start_coord - end_coord)
                length = np.count_nonzero(line)
                straightness = totally_straight / length
                f = {
                    'n_objects': n_subobjects,
                    'cut_object_solidity': solidity,
                    'cut_object_form_factor': form_factor,
                    'cut_object_area': area,
                    'min_intensity': np.min(intensity),
                    'mean_intensity': np.mean(intensity),
                    'median_intensity': np.median(intensity),
                    'max_intensity': np.max(intensity),
                    'length': length,
                    'straightness': straightness,
                    'min_blackness': np.min(blackness),
                    'mean_blackness': np.mean(blackness),
                    'median_blackness': np.median(blackness),
                    'max_blackness': np.max(blackness),
                }
                features.append(f)
            features = pd.DataFrame(features)
            features.index = pd.MultiIndex.from_tuples(
                lines.keys(), names=['start', 'end']
            )

            # TODO: Additional intensity criteria to prevent "stupid" cuts
            # e.g. only select line when intensity is below a certain global
            # intensity threshold.
            potential_line_index = (
                (features.n_objects == 2) &
                (features.cut_object_solidity > max_solidity) &
                (features.cut_object_form_factor > max_form_factor) &
                (features.cut_object_area > min_cut_area) &
                (features.mean_intensity < intensity_cutoff)
            )
            if not any(potential_line_index):
                logger.debug('no cut - no line passed tests')
                continue

            # potential_lines = [
            #     lines[idx]
            #     for idx in features.ix[potential_line_index].index.values
            # ]
            # plt.imshow((np.sum(potential_lines, axis=0) > 0) + mask * 2);
            # plt.show()

            # Select the "optimal" line based on its intensity profile, length
            # and straightness
            selected_features = features.loc[
                potential_line_index,
                ['median_intensity', 'median_blackness', 'length', 'straightness',
                    'cut_object_solidity', 'cut_object_form_factor']
            ]
            # TODO: optimize feature selection and weights
            # The line should be short and straight, intensity along the line should
            # be low and the cut object should be round.
            weights = np.array([2, -2, 2, -2, -1, -1])
            costs = selected_features.dot(weights)
            idx = costs[costs == np.min(costs)].index.values[0]

            # plt.imshow(mask + lines[idx]*2)
            # plt.show()

            # Update cut mask
            y, x = np.where(lines[idx])
            y_offset, x_offset = bboxes[oid][[0, 2]] - PAD
            y += y_offset
            x += x_offset
            cut_mask[y, x] = True

        output_mask[cut_mask] = 0

    output = dict()
    output['output_mask'] = output_mask
    if plot:
        from jtlib import plotting
        labeled_output_mask, n_objects = mh.label(
            output_mask, np.ones((3, 3), bool)
        )
        colorscale = plotting.create_colorscale(
            'Spectral', n=n_objects, permute=True, add_background=True
        )
        outlines = mh.morph.dilate(mh.labeled.bwperim(output_mask))
        cutlines = mh.morph.dilate(mh.labeled.bwperim(cut_mask))
        plots = [
            plotting.create_mask_image_plot(
                labeled_output_mask, 'ul', colorscale=colorscale
            ),
            plotting.create_intensity_overlay_image_plot(
                input_image, outlines, 'ur'
            ),
            plotting.create_mask_overlay_image_plot(
                clumps_mask, cutlines, 'll'
            )
        ]
        output['figure'] = plotting.create_figure(
            plots, title='separated clumps'
        )
    else:
        output['figure'] = str()

    return output
