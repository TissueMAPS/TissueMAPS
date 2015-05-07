"""
Utility functions for filename and path routines.
"""

import re
import os
import json
import yaml
from natsort import natsorted
from os.path import join, dirname, realpath, isdir
from scipy.misc import imread


SUPPORTED_IMAGE_FILES = ['png', 'jpg', 'tiff', 'jpeg']

# A regexp to detect supported files. Used to filter images in a directory.
_image_regex = re.compile('.*(' + '|'.join(
    ['\\.' + ext for ext in SUPPORTED_IMAGE_FILES]) + ')$', re.IGNORECASE)


def is_image(filename):
    "Check if filename ends with a supported file extension"
    return _image_regex.match(filename) is not None


class SiteImage:
    """Utility class for site images files"""

    # (height, width) just like numpy shape
    size = None

    def __init__(self, filename, row_nr, col_nr):
        if not os.path.isabs(filename):
            self.filename = os.path.abspath(filename)
        else:
            self.filename = filename
        self.row_nr = row_nr
        self.col_nr = col_nr

    @staticmethod
    def from_filename(filename, cfg):
        regexp = cfg['COORDINATE_FROM_FILENAME']
        m = re.search(regexp, filename)
        if not m:
            raise Exception('Can\'t create SiteImage object '
                            'from filename ' + filename)
        else:
            row_nr, col_nr = map(int, m.groups())
            if cfg['COORDINATES_IN_FILENAME_ONE_BASED']:
                row_nr -= 1
                col_nr -= 1
            return SiteImage(filename, row_nr, col_nr)

    def as_numpy_array(self):
        return imread(self.filename)

    def get_size(self):
        if not SiteImage.size:
            SiteImage.size = self.as_numpy_array().shape
        return SiteImage.size


class CycleDirectory:

    def __init__(self, filename, experiment_name, cycle_number):
        """Utility class for cycle directories"""
        self.filename = filename
        self.experiment_name = experiment_name
        self.cycle_number = cycle_number

    @staticmethod
    def is_correct_filename(filename, cfg):
        regexp = regex_from_format_string(cfg['CYCLE_SUBDIRECTORY_NAME_FORMAT'])
        return re.match(regexp, filename) is not None

    @staticmethod
    def from_filename(filename, cfg):
        regexp = regex_from_format_string(cfg['CYCLE_SUBDIRECTORY_NAME_FORMAT'])
        m = re.match(regexp, filename)
        if not m:
            raise Exception('Can\'t create CycleDirectory object '
                            'from filename ' + filename)
        else:
            return CycleDirectory(
                filename, m.group('experiment_name'),
                int(m.group('cycle_number')))

    def __str__(self):
        return '%s - %s' % (self.experiment_name, self.cycle_number)

    def __unicode__(self):
        return self.__str__()


class Cycles:

    def __init__(self, config_settings):
        """
        Configuration settings provided by YAML file.
        """
        self.cfg = config_settings

    def specify(self, root_dir):
        self.descriptors = self.load_shift_descrs(root_dir)
        self.directories = self.get_cycle_directories(root_dir)

    def load_shift_descrs(self, root_dir):
        """
        Load the shift descriptor json files according to the path
        given in the config file.
        """
        # Try to find all cycle subdirectories
        dir_content = os.listdir(root_dir)
        regexp = regex_from_format_string(self.cfg['CYCLE_SUBDIRECTORY_NAME_FORMAT'])

        def is_cycle_dir(dirname):
            return re.match(regexp, dirname) and isdir(join(root_dir, dirname))

        cycle_dirs = filter(is_cycle_dir, dir_content)
        shift_desc_location = self.cfg['SHIFT_DESCRIPTOR_FILE_LOCATION']
        descr_files = [shift_desc_location.format(cycle_subdirectory=cycle_dir)
                       for cycle_dir in cycle_dirs]
        descr_files = [join(root_dir, p) for p in descr_files]

        descrs = []
        for path in descr_files:
            with open(path, 'r') as f:
                descrs.append(json.load(f))
        self.descriptors = descrs
        return descrs

    def get_cycle_nr_from_filename(self, filename):
        try:
            return int(re.search(self.cfg['CYCLE_NR_FROM_FILENAME'], filename).groups()[0])
        except Exception as error:
            raise Exception('Can\'t get cycle number from filename %s\n%s'
                            % (filename, error))

    def get_cycle_directories(self, root_dir):
        dir_content = os.listdir(root_dir)
        dir_content = natsorted(dir_content)
        cycle_dirs = []
        for f in dir_content:
            if os.path.isdir(os.path.join(root_dir, f)) \
                    and CycleDirectory.is_correct_filename(f, self.cfg):
                cdir = CycleDirectory.from_filename(f, self.cfg)
                cycle_dirs.append(cdir)
        return cycle_dirs

    def get_shift_dir(self, root_dir, cycle_dir_object):
        return join(root_dir, self.cfg['SHIFT_FOLDER_LOCATION'].format(
            cycle_subdirectory=cycle_dir_object.filename))


class Image:

    def __init__(self, image_dir, image_files):
        self.directory = image_dir
        self.files = image_files


class Segmentation:

    def __init__(self, segmentation_dir, segmentation_files):
        self.directory = segmentation_dir
        self.files = segmentation_files


class Project:

    def __init__(self, config_settings):
        """
        Configuration settings provided by YAML file.
        """
        self.cfg = config_settings

    def specify(self, root_dir, cycle_dir_object=None):
        image_dir = self.get_image_dir(root_dir, cycle_dir_object)
        image_files = self.get_image_files(root_dir, cycle_dir_object)
        segmentation_dir = self.get_segmentation_dir(root_dir,
                                                     cycle_dir_object)
        segmentation_files = self.get_segmentation_files(root_dir,
                                                         cycle_dir_object)
        self.image = Image(image_dir, image_files)
        self.segmentation = Segmentation(segmentation_dir, segmentation_files)

    def get_channel_nr_from_filename(self, filename):
        try:
            return int(re.search(self.cfg['CHANNEL_NR_FROM_FILENAME'], filename).groups()[0])
        except Exception as error:
            raise Exception('Can\'t get channel number from filename %s'
                            % (filename, error))

    def get_expname_from_filename(self, filename):
        try:
            return re.search(self.cfg['EXPERIMENT_NAME_FROM_FILENAME'], filename).groups()[0]
        except Exception as error:
            raise Exception('Can\'t get experiment name from filename %s'
                            % (filename, error))

    def get_image_files(self, root_dir, cycle_dir_object=None):
        if cycle_dir_object:
            image_folder = join(root_dir, self.cfg['IMAGE_FOLDER_LOCATION'].format(
                cycle_subdirectory=cycle_dir_object.filename))
        else:
            image_folder = join(root_dir, self.cfg['IMAGE_FOLDER_LOCATION'])
        files = [join(image_folder, f) for f in os.listdir(image_folder)
                 if is_image(f)]
        files = natsorted(files)
        return files

    def get_image_dir(self, root_dir, cycle_dir_object=None):
        if cycle_dir_object:
            folder = join(root_dir, self.cfg['IMAGE_FOLDER_LOCATION'].format(
                cycle_subdirectory=cycle_dir_object.filename))
        else:
            folder = join(root_dir, self.cfg['IMAGE_FOLDER_LOCATION'])
        return folder

    def get_segmentation_files(self, root_dir, cycle_dir_object=None):
        if cycle_dir_object:
            image_folder = join(root_dir, self.cfg['SEGMENTATION_FOLDER_LOCATION'].format(
                cycle_subdirectory=cycle_dir_object.filename))
        else:
            image_folder = join(root_dir, self.cfg['SEGMENTATION_FOLDER_LOCATION'])
        files = [join(image_folder, f) for f in os.listdir(image_folder)
                 if is_image(f)]
        files = natsorted(files)
        return files

    def get_segmentation_dir(self, root_dir, cycle_dir_object=None):
        if cycle_dir_object:
            folder = join(root_dir, self.cfg['SEGMENTATION_FOLDER_LOCATION'].format(
                cycle_subdirectory=cycle_dir_object.filename))
        else:
            folder = join(root_dir, self.cfg['SEGMENTATION_FOLDER_LOCATION'])
        return folder

    def get_rootdir_from_image_file(self, imagefile):
        levels = len(self.cfg['IMAGE_FOLDER_LOCATION'].split('/'))
        root_dir = realpath(join(dirname(imagefile), * ['..'] * levels))
        return root_dir


def get_coord_by_regex(filename, pattern, one_based):
    """
    Get the coordinate for a filename assuming that the
    coordinate is encoded in the file's name.
    The returned coordinates must be 0-based!

    :filename: the image name : string
    :pattern:  the regex to extract the coordinates.
                  Needs 2 groups for row and col (in that order).
    :one_based: if the coordinates encoded in the file name are 1-based.
                If False they are assumed to be 0-based.
    :returns: 0-based row and column of the image : (int, int).

    """
    m = re.search(pattern, filename)
    if m is None:
        raise Exception(
            "Malformed filename! Couldn't extract row and column number with "
            "given regexp and filename: " + filename)
    else:
        row_nr, col_nr = map(int, m.groups())
        if one_based:
            return (row_nr - 1, col_nr - 1)
        else:
            return (row_nr, col_nr)


def regex_from_format_string(format_string):
    """
    Convert a format string of the sort
    '{experiment_name}_bla/something_{number}'
    to a named regular expression.
    """
    # Extract the names of all placeholders from the format string
    placeholders_inner_parts = re.findall(r'{(.+?)}', format_string)
    # Remove format strings
    placeholder_names = [pl.split(':')[0] for pl in placeholders_inner_parts]
    placeholder_regexes = [re.escape('{%s}') % pl
                           for pl in placeholders_inner_parts]

    regex = format_string
    for pl_name, pl_regex in zip(placeholder_names, placeholder_regexes):
        if re.search(r'number', pl_name):
            regex = re.sub(pl_regex, '(?P<%s>\d+)' % pl_name, regex)
        else:
            regex = re.sub(pl_regex, '(?P<%s>.*)' % pl_name, regex)

    return regex


def load_config(config_filename):
    '''Load project configuration from yaml file.'''
    if not os.path.exists(config_filename):
        raise Exception('Error: configuration file %s does not exist!'
                        % config_filename)
    return yaml.load(open(config_filename).read())


def check_config(config):
    yaml_keys = [
        'COORDINATE_FROM_FILENAME',
        'COORDINATES_IN_FILENAME_ONE_BASED',
        'SHIFT_DESCRIPTOR_FILE_LOCATION',
        'CYCLE_SUBDIRECTORY_NAME_FORMAT',
        'CYCLE_NR_FROM_FILENAME',
        'EXPERIMENT_NAME_FROM_FILENAME',
        'IMAGE_FOLDER_LOCATION',
        'SEGMENTATION_FOLDER_LOCATION',
        'SHIFT_FOLDER_LOCATION',
        'STATS_FOLDER_LOCATION',
        'STATS_FILE_FORMAT',
        'CHANNEL_NR_FROM_FILENAME',
        'MEASUREMENT_FOLDER_LOCATION',
        'CELL_ID_FORMAT'
    ]
    for key in yaml_keys:
        if key not in config:
            print('Error: configuration file must contain the key "%s"' % key)
