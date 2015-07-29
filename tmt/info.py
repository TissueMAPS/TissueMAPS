#!/usr/bin/env python
import os
import numpy as np
import yaml
import javabridge
import bioformats as bf
import tmt
import illuminati.stitch


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

    parser.add_argument('filename', type=str, help='path to image file')
    parser.add_argument('-o', '--output', dest='output_dir', required=True,
                        help='path to output directory')
    parser.add_argument('-s', '--save', dest='save_images',
                        action='store_true', default=False,
                        help='if extracted images should be saved')

    args = parser.parse_args()

    filename = args.filename

    if args.save_images:
        if not os.path.exists(args.output_dir):
            os.mkdir(args.output_dir)

    # NOTE: updated "loci_tools.jar" file to latest schema:
    # http://downloads.openmicroscopy.org/bio-formats/5.1.3
    jars = bf.JARS
    javabridge.start_vm(class_path=jars, run_headless=True)

    try:
        ome_xml = bf.get_omexml_metadata(filename)
        metadata = bf.OMEXML(ome_xml)

        n_images = metadata.get_image_count()
        images = list()
        print '%d images found' % n_images
        for i in xrange(n_images):
            images.append(dict())
            print '\nimage #%d:' % i

            pixels = metadata.image(i).Pixels  # image

            image_name = metadata.image(i).Name
            print '  name: {0}'.format(image_name)
            images[i]['name'] = image_name

            image_id = metadata.image(i).ID
            print '  id: {0}'.format(image_id)
            images[i]['id'] = image_id

            n_channels = pixels.get_channel_count()  # pixels.SizeC
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
                raise NotImplementedError('Only one time point is supported.')

            image_dtype = pixels.get_PixelType()
            print '  data type: {0}'.format(image_dtype)
            images[i]['type'] = image_dtype

            image_dimensions = (pixels.get_SizeY(), pixels.get_SizeX())
            print '  dimensions: {0}'.format(image_dimensions)
            images[i]['dimensions'] = image_dimensions

            # pixels.get_DimensionOrder()
            n_planes = pixels.get_plane_count()
            if n_planes > 0 or n_channels > 0 or n_zstacks > 0:
                if n_planes == 0:
                    positional_info_available = False
                    # Sometimes an image will not have any planes, although
                    # it contains multiple channels and/or z-stacks.
                    # In order to be able to apply the same logic downstream
                    # in the workflow, we create planes.
                    pixels.plane_count = n_channels * n_zstacks
                    order = pixels.get_DimensionOrder()
                    channel_position = order.index('C')
                    zstack_position = order.index('Z')
                    if zstack_position < channel_position:
                        count = -1
                        for z in xrange(n_zstacks):
                            for c in xrange(n_channels):
                                count += 1
                                pixels.Plane(count).TheZ = z
                                pixels.Plane(count).TheC = c
                                pixels.Plane(0).TheT = 0
                    else:
                        count = -1
                        for c in xrange(n_channels):
                            for z in xrange(n_zstacks):
                                count += 1
                                pixels.Plane(count).TheZ = z
                                pixels.Plane(count).TheC = c
                                pixels.Plane(0).TheT = 0
                else:
                    positional_info_available = True
                # Now we can inspect each plane individually
                n_planes = pixels.get_plane_count()
                images[i]['zstacks'] = {c: list() for c in xrange(n_channels)}
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
                    images[i]['zstacks'][c].append(p)
            else:
                # Does no planes automatically mean
                # n_zstacks=1 and n_channels=1?
                images[i]['zstacks'] = {0: [pixels]}

        if positional_info_available:
            # For debugging
            del images[-1]

            # Determine position of each image in the acquisition grid
            positions = [i['position'] for i in images]
            stich_dims = illuminati.stitch.calc_stitch_dimensions(positions)
            layout = illuminati.stitch.calc_stitch_layout(stich_dims,
                                                          positions)
            coords = illuminati.stitch.calc_image_position(stich_dims,
                                                           layout['zig_zag'],
                                                           layout['fill_order'])

        with bf.ImageReader(filename) as reader:
            info = dict()
            for i, img in enumerate(images):
                print 'image #%d' % (i + 1)
                # Separate channels
                for c, plane in img['zstacks'].iteritems():
                    print 'channel #%d' % (c + 1)
                    if img['n_zstacks'] > 1:
                        # Perform maximum intensity projection to generate a
                        # single-plane 2D image
                        stack = np.empty((len(plane),
                                          img['dimensions'][0],
                                          img['dimensions'][1]),
                                         dtype=img['type'])
                        for z, p in enumerate(plane):
                            stack[z, :, :] = reader.read(index=p, series=i,
                                                         rescale=False)
                        plane_img = np.max(stack, axis=0)

                        if args.save_images:
                            # Write image to file
                            # Since we also store the metadata per file in the
                            # YAML file, the actual filename doesn't matter
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
                            output_file = os.path.join(args.output_dir,
                                                       output_file)
                            bf.write_image(pathname=output_file,
                                           pixels=plane_img,
                                           pixel_type=image_dtype,
                                           channel_names=[img['channels'][c]])

        if args.save_images:
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
