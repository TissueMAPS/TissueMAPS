import os
import numpy as np
import javabridge
import bioformats
import visi.stk2png
import tmt
import illuminati.stitch

image_folder = '/Users/mdh/ilui/tests/images/leica'
image_file = 'P8_WT_animal8_serie1_section6_hippocampus_tilescan_20X_3.2.lif'

# image_folder = '/Users/mdh/ilui/tests/images/zeiss/'
# image_file = 'embryo_FL_20X_0002.czi'

filename = os.path.join(image_folder, image_file)

# TODO: how to update to newer schema?
# http://downloads.openmicroscopy.org/bio-formats/5.1.3/
# new_jar = '/Users/mdh/Envs/tmaps/lib/python2.7/site-packages/bioformats/jars/loci_tools.jar'
# jars = [new_jar] + bioformats.JARS
jars = bioformats.JARS
javabridge.start_vm(class_path=jars)
ome_xml = bioformats.get_omexml_metadata(filename)
metadata = bioformats.OMEXML(ome_xml)

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
    images[i]['channels'] = {c: str() for c in xrange(n_channels)}
    for channel in xrange(n_channels):
        channel_name = metadata.image(i).Pixels.Channel(channel).Name
        images[i]['channels'][channel] = channel_name

    n_zstacks = pixels.SizeZ
    print '  number of zstacks: {0}'.format(n_zstacks)
    images[i]['zstacks'] = n_zstacks

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
    images[i]['stacks'] = {c: list() for c in xrange(n_channels)}
    for p in xrange(n_planes):
        print '  plane #%d:' % p
        plane = metadata.image(i).Pixels.Plane(p)
        x = plane.get_PositionX()
        # print '    x position: {0}'.format(x)
        y = plane.get_PositionY()
        # print '    y position: {0}'.format(y)
        images[i]['position'] = (y, x)
        z = plane.get_TheZ()
        print '    zstack: {0}'.format(z)
        c = plane.get_TheC()
        print '    channel: {0}'.format(c)
        images[i]['stacks'][c].append(p)

# For debugging
del images[-1]

# Determine position of each image in the acquisition grid
positions = [i['position'] for i in images]
n_rows, n_columns = illuminati.stitch.determine_stitch_dims(positions)
layout = illuminati.stitch.determine_stitch_layout((n_rows, n_columns),
                                                   positions)
coords = illuminati.stitch.determine_image_position((n_rows, n_columns),
                                                    layout['zig_zag'],
                                                    layout['fill_order'])

with bioformats.ImageReader(filename) as reader:
    for i, img in enumerate(images):
        print 'image #%d' % (i + 1)
        for channel, plane in img['stacks'].iteritems():
            stack = np.empty((img['dimensions'][0],
                              img['dimensions'][1],
                              len(plane)), dtype=img['type'])
            print 'channel #%d' % (channel + 1)
            for z, p in enumerate(plane):
                stack[:, :, z] = reader.read(index=p, series=i, rescale=False)
            mip = np.max(stack, axis=2)
            # import ipdb; ipdb.set_trace()
            output_filename = tmt.config['IMAGE_FILE_FORMAT'].format(
                                                    experiment=img['name'],
                                                    cycle=1,
                                                    site=i+1,
                                                    row=coords[i][0],
                                                    column=coords[i][1],
                                                    channel=channel+1,
                                                    suffix='.png')
            output_filename = os.path.join(image_folder, 'output',
                                           output_filename)
            # bioformats.write_image(pathname=output_filename,
            #                        pixels=mip, pixel_type=image_dtype)
            visi.stk2png.write_png(output_filename, mip)

# TODO:
# if n_images > 0:
#   load all images stored in `filename`
# 
# write to disk as OME-TIFF files
# (and attach the corresponding metadata as OME-XML)
# 
# write the metadata for each image into the `image_info.yaml` file

# TODO: how to handle plates?
n_plates = len(metadata.plates)
if n_plates > 0:
    print 'PLATE format'
for p in xrange(n_plates):
    plate = metadata.plates[p]

javabridge.kill_vm()
