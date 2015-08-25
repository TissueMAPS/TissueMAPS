def create_channel_planes(pixels):
    '''
    Add new *Plane* elements to an existing OME *Pixels* object,
    such that z-stacks are grouped by channel.

    Parameters
    ----------
    pixels: bioformats.omexml.Pixels
        OME Pixels object

    Returns
    -------
    bioformats.omexml.Pixels
        OME Pixels object with added Plane element
    '''
    n_channels = pixels.SizeC
    n_zstacks = pixels.SizeZ
    pixels.plane_count = n_channels * n_zstacks
    channel_position = pixels.DimensionOrder.index('C')
    zstack_position = pixels.DimensionOrder.index('Z')
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
    return pixels
