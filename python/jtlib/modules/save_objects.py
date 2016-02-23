import numpy as np
import logging
import cv2
import plotly
import colorlover as cl
# import SimpleITK as sitk
import skimage.measure
from tmlib.writers import DatasetWriter
import jtlib.utils
import jtlib.plotting

logger = logging.getLogger(__name__)


def save_objects(image, name, **kwargs):
    '''
    Jterator module for saving a segmentation image, i.e. a labeled image where
    each label encode a segmented object.

    Parameters
    ----------
    image: numpy.ndarray
        labeled image where pixel value encodes objects id
    name: str
        name that should be given to the objects in `image`
    **kwargs: dict
        additional arguments provided by Jterator:
        "data_file", "figure_file", "experiment_dir", "plot", "job_id"
    '''
    objects_ids = np.unique(image[image > 0])
    border_indices = jtlib.utils.find_border_objects(image)

    y_coordinates = list()
    x_coordinates = list()

    # Set border pixels to background to find complete contours of border objects
    image[0, :] = 0
    image[-1, :] = 0
    image[:, 0] = 0
    image[:, -1] = 0

    for obj_id in objects_ids:
        # Find the contours of the current object
        # We could do this for all objects at once, but doing it for each
        # object individually ensures that we get the correct number of objects
        # and that the coordinates are in the correct order, i.e. sorted by
        # label
        obj_im = image == obj_id
        contours = skimage.measure.find_contours(
                        obj_im, 0.5, fully_connected='high')
        # contours = sitk.BinaryContourImageFilter(obj_im)
        # contours = cv2.findContours(
        #                 obj_im.astype(np.uint8),
        #                 mode=cv2.RETR_EXTERNAL,
        #                 method=cv2.CHAIN_APPROX_SIMPLE
        # )[1]
        if len(contours) > 1:
            logger.warn('%d contours identified for object #%d',
                        len(contours), obj_id)
        contour = contours[0]
        # # We want the y coordinate in the first and the x coordinate in the
        # # second column, since this is what most scipy functions expect
        # contour = np.fliplr(np.vstack(contours[0]))
        # # Points need to be in counter-clockwise order
        # contour = jtlib.utils.sort_coordinates_counter_clockwise(contour)
        # # The contour has to be closed, i.e. the first and last entry have to
        # # the same (duplicated)
        # contour = np.vstack([contour, contour[0, :]])
        y = contour[:, 0].astype(np.int64)
        x = contour[:, 1].astype(np.int64)
        y_coordinates.append(y)
        x_coordinates.append(x)

    regions = skimage.measure.regionprops(image)
    if len(objects_ids) > 0:
        centroids = np.array([r.centroid for r in regions]).astype(np.int64)
    else:
        centroids = np.empty((0, 2)).astype(np.int64)

    group_name = '/objects/%s/segmentation' % name
    with DatasetWriter(kwargs['data_file']) as f:
        f.write('%s/ids' % group_name, data=objects_ids)
        f.write('%s/is_border' % group_name, data=border_indices)
        f.write('%s/centroids/y' % group_name, data=centroids[:, 0])
        f.write('%s/centroids/x' % group_name, data=centroids[:, 1])
        f.write('%s/coordinates/y' % group_name, data=y_coordinates)
        f.write('%s/coordinates/x' % group_name, data=x_coordinates)

    if kwargs['plot']:
        outline_image = np.zeros(image.shape, dtype=np.int64)
        for i, obj in enumerate(objects_ids):
            outline_image[y_coordinates[i], x_coordinates[i]] = obj

        # colors = cl.to_rgb(cl.interp(cl.scales['9']['div']['Spectral'], len(objects_ids)+1))
        # colors[0] = 'rgb(255,255,255)'
        data = [
            plotly.graph_objs.Heatmap(
                z=outline_image,
                hoverinfo='z',
                # colorscale=colors,
                colorscale='Hot',
                y=np.linspace(image.shape[0], 0),
                x=np.linspace(0, image.shape[1])
            )
            # plotly.graph_objs.Scatter(
            #     x=x_coordinates,
            #     y=y_coordinates,
            #     mode='lines'
            # )
        ]

        layout = plotly.graph_objs.Layout(
            title='Outlines of saved "%s" objects' % name,
            yaxis=plotly.graph_objs.YAxis(
                ticks='',
                showticklabels=False
            ),
            xaxis=plotly.graph_objs.XAxis(
                ticks='',
                showticklabels=False
            )
        )

        fig = plotly.graph_objs.Figure(data=data, layout=layout)
        jtlib.plotting.save_plotly_figure(fig, kwargs['figure_file'])
