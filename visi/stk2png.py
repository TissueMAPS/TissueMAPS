import os
import tifffile
import png
import numpy as np
from copy import copy
import re

import ipdb as db

# TODO: handle exceptions
# - single site acquisitions with no row/column info
# - no z-stacks
# - multiple time points
# - single acquisitions with no cycle info


def read_stk(stk_filename):
    '''
    Read stk file from disk and unpack individual images (z-stacks).
    Store it in a numpy array.
    '''
    # Something goes wrong with reading/writing!!!
    stack = tifffile.imread(stk_filename)
    return stack


def write_png(png_filename, image):
    ''' Write numpy array to disk as png.'''
    with open(png_filename, 'wb') as f:
        writer = png.Writer(width=image.shape[1],
                            height=image.shape[0],
                            bitdepth=16, greyscale=True)
        im_list = image.tolist()
        writer.write(f, im_list)


def read_nd(nd_filename):
    '''
    Read the content of the .nd file and do some pre-formatting.
    '''
    # Read content
    f = open(nd_filename, 'r')
    content = f.readlines()
    f.close()
    # Extract information and store it in a dictionary
    nd = dict()
    for line in content:
        if re.search('NDInfoFile', line) or re.search('EndFile', line):
            continue
        matched = re.search(r'"(.*)", (.+)\r', line)
        key = matched.group(1)
        value = matched.group(2)
        nd[key] = value
    return nd


def format_nd(nd):
    '''
    Format .nd file content, i.e. translate it into python syntax.
    Important keys:
        - DoStage       -> 'well'
        - DoTimelapse   -> 'time'
        - DoWave        -> 'channel'
        - DoZSeries     -> 'zstack'
    '''
    for k, v in nd.iteritems():
        string_match = re.search(r'"(.+)"', v)
        number_match = re.search(r'(\d+)', v)
        if v == 'TRUE':
            nd[k] = True
        elif v == 'FALSE':
            nd[k] = False
        elif string_match:
            nd[k] = string_match.group(1)
        elif number_match:
            nd[k] = int(number_match.group(1))
    return nd


def get_well_ids(nd):
    '''
    Get information on well position (well id) from .nd files.
    '''
    wells = [v for k, v in nd.iteritems() if re.search(r'Stage\d+', k)]
    well_info = [re.search(r'row:(\w),column:(\d+)', w) for w in wells]
    well_ids = [''.join(map(w.group, xrange(1, 3))) for w in well_info]
    return well_ids


def guess_stitch_dims(max_position, layout):
    '''
    Simply algorithm to guess correct dimensions of the stitched image.
    :max_position:  integer giving the maximum position in the image
    :layout:        string for more rows than columns ('columns<rows')
                    or vice versa ('columns>rows')
    '''
    if layout == 'columns<rows':
        decent = True
    elif layout == 'columns>rows':
        decent = False
    else:
        raise Exception('Layout needs to be specified.')
    tmpI = np.arange((int(np.sqrt(max_position)) - 5),
                     (int(np.sqrt(max_position)) + 5))
    tmpII = np.matrix(tmpI).conj().T * np.matrix(tmpI)
    (a, b) = np.where(np.triu(tmpII) == max_position)
    stitch_dims = sorted([tmpI[a[0]], tmpI[b[0]]], reverse=decent)
    return stitch_dims


def get_image_snake(stitch_dims, acquisition_layout, doZigZag):
    '''
    The image snake defines the position of each image in the stitched
    image. Returns a list of 'row' and 'column' index of each 'site'.
    :stitch_dims:   list of the dimensions of the stitched image [rows, columns]
    :doZigZag:      bool indicating whether images were acquired in
                    "ZigZag" mode
    '''
    cols = []
    rows = []
    # Currently, only horizontal snakes are supported!
    for i in xrange(stitch_dims[0]):  # loop over rows
        # Change order of sites in columns if acquired in ZigZag mode
        if i % 2 and doZigZag:
            cols += range(stitch_dims[1], 0, -1)
        # Preserve order of sites in columns
        else:
            cols += range(1, stitch_dims[1]+1, 1)
        rows += [i+1 for x in range(stitch_dims[1])]
    snake = {'row': rows, 'column': cols}
    return snake


class Stk2png(object):

    def __init__(self, input_files, nd_file, config=None):
        '''
        Class for unpacking .stk files outputted from Visitron microscopes
        and conversion to .png format (with optional file renaming).
        :input_files:           list of the .stk filenames
        :nd_file:               filename of corresponding .nd file
        :config:                dictionary with configuration file content

        The config dictionary should contain the following keys:
         * nomenclature         string defining filename format using '{}'
         * acquisition_mode     string specifying the order in which images
                                were acquired (snake)
         * acquisition_layout   'rows>columns' (more rows than columns) or
                                'columns>rows' (vice versa)
        '''
        self.input_files = map(os.path.basename, input_files)
        self.output_files = copy(self.input_files)
        self.input_dir = os.path.dirname(input_files[0])
        self.nd_file = os.path.basename(nd_file)
        if config:
            self.filename_pattern = '(?:sdc|dualsdc|hxp|tirf|led)(.*)_s(\d+).stk'
            self.filter_pattern = '.*?([^mx]+[0-9]?)(?=xm)'
            self.tokens = ['filter', 'site']
            self.nomenclature = copy(config['FILENAME_FORMAT'])
            self.acquistion_mode = copy(config['ACQUISITION_MODE'])
            self.acquisition_layout = copy(config['ACQUISITION_LAYOUT'])
        else:
            self.filename_pattern = None
            self.filter_pattern = None
            self.tokens = None
            self.nomenclature = None
            self.acquistion_mode = None
            self.acquisition_layout = None

    def get_info_from_nd_files(self):
        '''
        Not all image information can be retrieved form the filename.
        We have to read additional meta information from the .nd files,
        in particular information on the position within the well plate.
        '''
        nd_filename = os.path.join(self.input_dir, self.nd_file)
        nd = read_nd(nd_filename)
        nd = format_nd(nd)

        metainfo = dict()
        metainfo['hasWell'] = nd['DoStage']
        metainfo['hasTime'] = nd['DoTimelapse']
        metainfo['hasChannel'] = nd['DoWave']
        metainfo['hasZStack'] = nd['DoZSeries']
        metainfo['nrChannel'] = nd['NWavelengths']
        metainfo['hasCycle'] = False
        self.metainfo = metainfo

        # Preallocate the variables that are inserted in the output filename
        if 'well' in self.metainfo['hasWell']:
            well_ids = get_well_ids(nd)
            self.info['well'] = well_ids

    def get_info_from_filenames(self):
        '''
        Get image information (such as channel, site, etc.) from filenames.
        '''
        info = self.info
        pattern = self.filename_pattern
        # Handle exceptions for 'time' and 'channel', which are not always
        # present in the filename
        if self.metainfo['hasTime']:
            pattern = re.sub(r'(.*)\.stk$', '\\1_t(\d+).stk', pattern)
            self.tokens = self.tokens + ['time']
        else:
            info['time'] = [1 for x in xrange(len(self.input_files))]
        if self.metainfo['hasChannel']:
            pattern = '%s%s' % ('_w(\d)', pattern)
            self.tokens = ['channel'] + self.tokens
        else:
            info['channel'] = [0 for x in xrange(len(self.input_files))]
        # Information on zstacks is handled separately
        info['zstack'] = [0 for x in xrange(len(self.input_files))]
        # The project name can be easily retrieved from .nd filename
        project_name = re.search(r'(.*)\.nd$', self.nd_file).group(1)
        info['project'] = [project_name for x in xrange(len(self.input_files))]
        for stk_file in self.input_files:
            # Retrieve information for 'filter' from filename
            r = re.compile('%s%s' % (project_name, pattern))
            matched = re.search(r, stk_file)
            if not matched:
                raise Exception('"Filter" info could not be extracted from filenames')
            matched = map(matched.group, range(1, len(self.tokens)+1))
            for i, t in enumerate(self.tokens):
                # Handle special cases that are more complex
                if t == 'filter':
                    if re.search(r'xm', matched[i]):
                        r = re.compile(self.filter_pattern)
                        match = re.search(r, matched[i]).group(1)
                    # TODO: handles dual sdc mode!
                    else:
                        match = matched[i]
                else:
                    match = matched[i]
                try:
                    info[t].append(match)
                except:
                    raise Exception('... Token "%s" didn\'t match filename.' % t)
        # Assert correct data type (string, interger, etc)
        convert_to_int = ['site', 'channel']
        for i in convert_to_int:
            if i in info:
                info[i] = map(int, info[i])
        self.info = info

        if 'well' in self.info and self.metainfo['hasWell']:
            # Map well ids to filenames
            unique_sites = np.unique(self.info['site'])
            if len(self.info['well']) is not len(unique_sites):
                raise Exception('Number of well positions doesn\'t match ',
                                'number of sites!')
            well_ids = np.chararray(len(self.info['site']), itemsize=3)
            for i, site in enumerate(unique_sites):
                ix = np.where(np.array(self.info['site']) == site)
                well_ids[ix] = self.info['well'][i]
            self.info['well'] = well_ids.tolist()
        else:
            self.info['well'] = [0 for x in xrange(len(self.input_files))]

    def get_image_position(self):
        '''
        Get the position of images within the overall imaging area (e.g. well).
        :mode:       string specifying the image acquisition order
        '''
        if self.acquistion_mode == 'ZigZagHorizontal':
            doZigZag = True
        elif self.acquistion_mode == 'Horizontal':
            doZigZag = False
        else:
            raise Exception('The provided acquisition mode is not supported.')

        sites = self.info['site']
        max_pos = max(sites)
        stitch_dims = guess_stitch_dims(max_pos, self.acquisition_layout)
        snake = get_image_snake(stitch_dims, self.acquisition_layout, doZigZag)
        column = np.array([None for x in xrange(len(sites))])
        row = np.array([None for x in xrange(len(sites))])
        for i, s in enumerate(np.unique(sites)):
            ix = np.where(sites == s)[0]
            column[ix] = snake['column'][i]
            row[ix] = snake['row'][i]
        self.info['column'] = map(int, column)
        self.info['row'] = map(int, row)

    def rename_files(self):
        '''
        Rename files according to a user-defined nomenclature.
        :rename:    bool defining whether files should be renamed
        '''
        renamed_files = [self.nomenclature for x in xrange(len(self.input_files))]
        for i in xrange(len(renamed_files)):
            try:
                renamed_files[i].format(project=self.info['project'][i],
                                        well=self.info['well'][i],
                                        site=self.info['site'][i],
                                        row=self.info['row'][i],
                                        column=self.info['column'][i],
                                        zstack=self.info['zstack'][i],
                                        time=self.info['time'][i],
                                        filter=self.info['filter'][i],
                                        channel=self.info['channel'][i])
            except TypeError as error:
                raise Exception('Formatting "%s" failed:\n%s' %
                                (self.input_files[i], error))
        self.output_files = renamed_files

    def unpack_images(self, output_dir, keep_z=False, indices=None):
        '''
        Read and upstack stk files and write images (z-stacks or MIPs)
        to disk as .png files.
        :indices:       list of integers specifying which files are processed,
                        one-based (by default all files are processed)
        :output_dir:    string specifying directory where images are saved
        :keep_z:        bool to keep individual z stacks
                        (if `False` MIPs are generated - default)
        '''
        if indices is None:
            # Process all files if no indices are provided
            indices = range(len(self.input_files))

        for i in indices:
            stk_file = self.input_files[i]
            print '.... Unpack file "%s"' % stk_file
            stack = read_stk(os.path.join(self.input_dir, stk_file))
            output_file = re.sub(r'\.stk$', '.png', self.output_files[i])
            if keep_z and self.metainfo['hasWell']:
                # Keep individual z-stacks
                for z in xrange(stack.shape[0]):
                    # Encode 'zstack' info in filename
                    output_file_z = re.sub(r'_z00', '_z%.2d' % z, output_file)
                    print '.... Write file "%s"' % output_file_z
                    write_png(os.path.join(output_dir, output_file_z),
                              stack[z])
            else:
                # Perform maximum intensity projection (MIP)
                # Should also work if there is only one image (i.e. no stacks)
                mip = np.array(np.max(stack, axis=0), dtype=stack[0].dtype)
                print '.... Write file "%s"' % output_file
                write_png(os.path.join(output_dir, output_file), mip)
