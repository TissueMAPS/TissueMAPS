from ..formats import Formats

INIT_ARGS = [
    {
        'name': 'format',
        'short_name': 'f',
        'type': str,
        'choices': Formats.SUPPORT_FOR_ADDITIONAL_FILES,
        'help': '''
            microscope-specific file format for which custom
            readers are available (default: "default")
        '''
    },
    {
        'name': 'z_stacks',
        'short_name': 'z',
        'type': bool,
        'help': '''
            if individual focal planes should be kept,
            i.e. no intensity project performed
        '''
    }
]


# init_group.add_argument(
#     '-f', '--format', type=str, default='default',
#     choices=Formats.SUPPORT_FOR_ADDITIONAL_FILES,
#     help='microscope-specific file format for which custom '
#          'readers are available (default: "default")')
# init_group.add_argument(
#     '-z', '--z_stacks', action='store_true',
#     help='if individual focal planes should be kept, '
#          'i.e. no intensity project performed')
# init_group.add_argument(
#     '-r', '--regex', type=str, default=None, metavar='expression',
#     help='named regular expression that defines group names "(?P<name>...)" '
#          'for retrieval of metadata from image filenames')
# init_group.add_argument(
#     '--stitch_major_axis', type=str, default='vertical',
#     choices={'vertical', 'horizontal'},
#     help='specify which axis of the stitched mosaic image is longer '
#          '(default: "vertical")')
# init_group.add_argument(
#     '--stitch_vertical', type=int, default=None, metavar='N_ROWS',
#     help='number of images along the vertical axis of each stitched mosaic')
# init_group.add_argument(
#     '--stitch_horizontal', type=int, default=None, metavar='N_COLUMNS',
#     help='number of images along the horizontal axis of each stitched mosaic')
# init_group.add_argument(
#     '--stitch_layout', type=str, default='zigzag_horizontal',
#     choices={'horizontal', 'zigzag_horizontal', 'vertical', 'zigzag_vertical'},
#     help='layout of the stitched mosaic image, i.e. the order in '
#          'which images are arrayed on the grid (default: "zigzag_horizontal")')
