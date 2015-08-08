#!/usr/bin/env python
import os
import glob
import numpy as np
import yaml
import javabridge
import bioformats as bf
import tmt
from illuminati import stitch

'''
Module for collecting information on image files, such as the site and
channel number. Some information is retrieved form the xml metadata attached
to the image files using
`Bio-Formats <http://www.openmicroscopy.org/site/products/bio-formats>`_.
Additional information that cannot be extracted from the metadata
has to be provided via configuration settings.
'''

# TODO: Well plates!

# Single file containing multiple "planes":
#   - stitch dimensions can be retrieved from the metadata
#   - channel information can be retrieved form the metadata
#   -> create individual image for each plane and channel
# 
# Several files, each containing a single "plan" with multiple "channels"
# (and "zstacks"):
#   - create "plane" for each "channel" and "zstack"
#   - stitch dimensions have to be provided
#   - channel information can be retrieved form the metadata 
#   -> create projection image
# 
# Several files, each containing multiple "zstacks" (e.g. .stk file):
#   - stitch dimensions have to be provided
#   - channel information has to be provided (or retrieved form filename
#     or additional metadata file, e.g. Metamorph/Visitron .nd file or
#     Yokogawa .xml file)
#   -> create projection image
# 
# Several files, each containing a single 2D image with only one "channel":
#   - stitch dimensions have to be provided
#   - channel information has to be provided (or retrieved form filename
#     or additional metadata file, e.g. Metamorph/Visitron .nd file or
#     Yokogawa .xml file)


# For debugging
CUSTOM_IMAGE_FILE_FORMAT = \
    '{experiment}_{cycle:0>2}_s{site:0>4}_C{channel:0>2}{suffix}'


def write_image_info(filename, information):
    '''
    Write information about images, such as channel number or row/column
    position in the acquisition grid, obtained via Bio-Formats from the XML
    metadata to file in YAML format:

    .. code-block::

        <image_filename>:
            site: int
            row: int
            column: int

        <image_filename>:
            site: int
            row: int
            column: int

        ...


    Parameters
    ----------
    filename: str
        path to the file into which `information` should be written
    information: Dict[str, Dict[str, int or str]]
        metadata for each individual image, where each key is the filename of
        the image and the corresponding value is a dictionary specifying
        "site", "row", "column" and optionally "cycle", "channel" and "objects"

    See also
    --------
    `image`_
    '''
    with open(filename, 'w') as output:
        output.write(yaml.dump(information, default_flow_style=False))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Use Bio-Formats to extract images and metadata from '
                    'vendor-specific image formats.')

    parser.add_argument('image_folder', type=str, help='path to image file')

    parser.add_argument('-w', '--wildcards', dest='wildcards',
                        type=str, default='*',
                        help='wildcards (globbing patterns) '
                             'to select subset of files in "image_folder"')
    parser.add_argument('-o', '--output', dest='output_dir', type=str,
                        help='path to output directory, '
                             'where images should be saved')
    parser.add_argument('-s', '--save', dest='save_images',
                        action='store_true', default=False,
                        help='if extracted images should be saved')
    parser.add_argument('-i', '--info', dest='save_info',
                        action='store_true', default=False,
                        help='if metadata information should be saved')

    parser.add_argument('--info_config', dest='info_config',
                        help='use custom yaml configuration file \
                             (defaults to "info" configuration)')

    parser.add_argument('-c', '--config', dest='config',
                        help='use custom yaml configuration file \
                             (defaults to "tmt" configuration)')

    args = parser.parse_args()

    files = glob.glob(args.image_folder, args.wildcards)

    if args.save_images:
        if not os.path.exists(args.output_dir):
            os.mkdir(args.output_dir)

    if args.config:
        # Overwrite default "tmt" configuration
        print '. Using configuration file "%s"' % args.config
        args.config = tmt.utils.load_config(args.config)
        tmt.utils.check_config(args.config)
    else:
        args.config = tmt.config

    if 'info_config' in args:
        if args.info_config:
            # Overwrite default "visi" configuration
            print '. Using configuration file "%s"' % args.info_config
            args.config_file = args.config.copy()
            info_configuration = tmt.utils.load_config(args.info_config)
        else:
            info_configuration = tmt.info.config
            args.config_file = ''
    else:
        info_configuration = tmt.info.config
        args.config_file = ''

    # Add "info" to "tmt" configuration
    args.config.update(info_configuration)
    cfg = args.config

    # NOTE: updated "loci_tools.jar" file to latest schema:
    # http://downloads.openmicroscopy.org/bio-formats/5.1.3
    jars = bf.JARS
    javabridge.start_vm(class_path=jars, run_headless=True)

    # NOTE: The "try" is required to kill the java VM in case of an error
    try:
        for filename in files:
            print 'processing file "%s":' % filename
            # Retrieve information from metadata
            try:
                ome_xml = bf.get_omexml_metadata(filename)
                metadata = bf.OMEXML(ome_xml)
                if not metadata:
                    raise NotImplementedError('File format is not supported.')
            except Exception as e:
                raise NotImplementedError('File format is not supported.')

            n_images = metadata.get_image_count()
            images = list()
            print ' %d images found' % n_images
            for i in xrange(n_images):
                images.append(dict())
                print ' \nimage #%d:' % i

                pixels = metadata.image(i).Pixels  # the image

                image_name = metadata.image(i).Name
                print '  name: {0}'.format(image_name)
                images[i]['name'] = image_name

                image_id = metadata.image(i).ID
                print '  id: {0}'.format(image_id)
                images[i]['id'] = image_id

                n_channels = pixels.SizeC  # pixels.get_channel_count()
                print '  number of channels: {0}'.format(n_channels)
                images[i]['n_channels'] = n_channels
                images[i]['channels'] = {c: str() for c in xrange(n_channels)}
                for channel in xrange(n_channels):
                    channel_name = metadata.image(i).Pixels.Channel(channel).Name
                    images[i]['channels'][channel] = channel_name

                n_zstacks = pixels.SizeZ
                print '  number of zstacks: {0}'.format(n_zstacks)
                images[i]['n_zstacks'] = n_zstacks

                n_timepoints = pixels.SizeT
                print '  number of timepoints: {0}'.format(n_timepoints)
                if n_timepoints > 1:
                    raise NotImplementedError('Multiple time points '
                                              'are not supported.')

                image_dtype = pixels.get_PixelType()
                print '  data type: {0}'.format(image_dtype)
                images[i]['type'] = image_dtype

                image_dimensions = (pixels.get_SizeY(), pixels.get_SizeX())
                print '  dimensions: {0}'.format(image_dimensions)
                images[i]['dimensions'] = image_dimensions

                n_planes = pixels.get_plane_count()
                if n_planes > 0 or n_channels > 0 or n_zstacks > 0:
                    if n_planes == 0:
                        print '  no planes found - creating new' % n_planes
                        positional_info_available = False
                        # "plane": other dimensions that x,y
                        # Sometimes an image will not have any planes, although
                        # it contains multiple channels and/or z-stacks.
                        # In order to be able to apply the same workflow later,
                        # we create new planes.
                        pixels.plane_count = n_channels * n_zstacks
                        order = pixels.get_DimensionOrder()
                        channel_position = order.index('C')
                        zstack_position = order.index('Z')
                        if zstack_position < channel_position:
                            count = -1
                            for z in xrange(n_zstacks):
                                for c in xrange(n_channels):
                                    print('  creating new plane for '
                                          'channel #%d and stack #%d' % (c, z))
                                    count += 1
                                    pixels.Plane(count).TheZ = z
                                    pixels.Plane(count).TheC = c
                                    pixels.Plane(0).TheT = 0
                        else:
                            count = -1
                            for c in xrange(n_channels):
                                for z in xrange(n_zstacks):
                                    print('  creating new plane for '
                                          'channel #%d and stack #%d' % (c, z))
                                    count += 1
                                    pixels.Plane(count).TheZ = z
                                    pixels.Plane(count).TheC = c
                                    pixels.Plane(0).TheT = 0
                    else:
                        print '  %d planes found' % n_planes
                        positional_info_available = True
                    # Now we can inspect each plane individually
                    n_planes = pixels.get_plane_count()
                    images[i]['planes'] = {c: list() for c in xrange(n_channels)}
                    for p in xrange(n_planes):
                        print '  plane #%d:' % p
                        plane = metadata.image(i).Pixels.Plane(p)
                        x = plane.get_PositionX()
                        print '    x position: {0}'.format(x)
                        y = plane.get_PositionY()
                        print '    y position: {0}'.format(y)
                        images[i]['position'] = (y, x)
                        z = plane.get_TheZ()
                        print '    zstack: {0}'.format(z)
                        c = plane.get_TheC()
                        print '    channel: {0}'.format(c)
                        images[i]['planes'][c].append(p)
                else:
                    # We are dealing with a single plane
                    # TODO: do we have the channel information?
                    # Otherwise we have to add it.
                    images[i]['planes'] = {0: [pixels]}

            if positional_info_available:
                # For debugging of Leica .lif format
                del images[-1]

                # Determine position of each image in the acquisition grid
                pos = [i['position'] for i in images]
                stich_dims = stitch.calc_stitch_dimensions(pos)
                layout = stitch.calc_stitch_layout(stich_dims, pos)
                coords = stitch.calc_image_position(stich_dims, layout)
            else:
                # If we were not able to retrieve positional information from
                # the metadata we depend on the user to provide it via
                # the configuration settings.
                # TODO: outsource this step and write positional information
                # into the metadata
                n_sites = len(images)
                stich_dims = stitch.guess_stitch_dimensions(
                                    n_sites, cfg['MORE_ROWS_THAN_COLUMNS'])
                coords = stitch.calc_image_position(
                                    stich_dims, cfg['ACQUISITION_LAYOUT'])

            import ipdb; ipdb.set_trace()

            with bf.ImageReader(filename) as reader:
                info = dict()
                for i, img in enumerate(images):
                    print 'image #%d' % (i + 1)
                    # Separate channels
                    for c, plane in img['planes'].iteritems():
                        print 'channel #%d' % (c + 1)
                        if img['n_zstacks'] > 1:
                            # Perform maximum intensity projection to generate a
                            # single-plane 2D image
                            stack = np.empty((img['dimensions'][0],
                                              img['dimensions'][1],
                                              len(plane)),
                                             dtype=img['type'])
                            for z, p in enumerate(plane):
                                stack[:, :, z] = reader.read(index=p, series=i,
                                                             rescale=False)
                            plane_img = np.max(stack, axis=2)

                            # Write image to file
                            # Since we also store the metadata per file in the
                            # YAML file, the actual filename doesn't matter.
                            # NOTE: The retrieved image names are sometimes weird,
                            # consider using alternative names for the "experiment"
                            # keyword.
                            if positional_info_available:
                                output_file = (tmt.config['IMAGE_FILE_FORMAT']
                                               .format(experiment=img['name'],
                                                       cycle=1,
                                                       site=i+1,
                                                       row=coords[i][0],
                                                       column=coords[i][1],
                                                       channel=c+1,
                                                       suffix='.tif'))
                                info[os.path.basename(output_file)] = {
                                    'site': i+1,
                                    'row': coords[i][0],
                                    'column': coords[i][1],
                                    'cycle': 1,
                                    'channel': c+1
                                }
                            else:
                                output_file = (CUSTOM_IMAGE_FILE_FORMAT
                                               .format(experiment=img['name'],
                                                       cycle=1,
                                                       site=i+1,
                                                       channel=c+1,
                                                       suffix='.tif'))
                                info[os.path.basename(output_file)] = {
                                    'site': i+1,
                                    'cycle': 1,
                                    'channel': c+1
                                }
                            if args.save_images:
                                output_file = os.path.join(args.output_dir,
                                                           output_file)
                                bf.write_image(pathname=output_file,
                                               pixels=plane_img,
                                               pixel_type=image_dtype,
                                               channel_names=[img['channels'][c]])

            if args.save_info:
                info_filename = os.path.join(args.output_dir,
                                             tmt.config['IMAGE_INFO_FILE_FORMAT'])
                write_image_info(info_filename, info)

            # TODO: 
            # 
            # write as OME-TIFF files
            # (and attach the corresponding metadata as OME-XML)
            # 
            # write the metadata for each image into the `image_info.yaml` file

            # TODO: how to handle plates?
            n_plates = len(metadata.plates)
            if n_plates > 0:
                print 'PLATE format'
            for p in xrange(n_plates):
                plate = metadata.plates[p]

    finally:
        javabridge.kill_vm()
