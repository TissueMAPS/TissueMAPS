from . import __version__
from .cli import Metaconfig
from ..formats import Formats


parser, subparsers = Metaconfig.get_parser_and_subparsers()

parser.description = '''
        Convert metadata extracted from image files to a custom format
        and complement it with additional information.
    '''
parser.version = __version__

init_parser = subparsers.choices['init']
init_auto_group = init_parser.add_argument_group(
    'arguments for automatic formatting')
init_auto_group.add_argument(
    '-f', '--format', type=str, default='default',
    choices=Formats.SUPPORT_FOR_ADDITIONAL_FILES,
    help='specify a microscope-specific file format for which special '
         'readers are available (default: "default")')
init_auto_group.add_argument(
    '-z', '--z_stacks', action='store_true',
    help='if individual focal planes should be kept, '
         'i.e. no intensity project should be performed')

init_manual_group = init_parser.add_argument_group(
    'arguments for manual formatting')
init_manual_group.add_argument(
    '-r', '--regex', type=str, default=None, metavar='expression',
    help='named regular expression that defines group names "(?P<name>...)" '
         'for retrieval of metadata from image filenames')
init_manual_group.add_argument(
    '--stitch_major_axis', type=str, default='vertical',
    choices={'vertical', 'horizontal'},
    help='specify which axis of the stitched mosaic image is longer '
         '(default: "vertical")')
init_manual_group.add_argument(
    '--stitch_vertical', type=int, default=None, metavar='N_ROWS',
    help='number of images along the vertical axis of each stitched mosaic')
init_manual_group.add_argument(
    '--stitch_horizontal', type=int, default=None, metavar='N_COLUMNS',
    help='number of images along the horizontal axis of each stitched mosaic')
init_manual_group.add_argument(
    '--stitch_layout', type=str, default='zigzag_horizontal',
    choices={'horizontal', 'zigzag_horizontal', 'vertical', 'zigzag_vertical'},
    help='layout of the stitched mosaic image, i.e. the order in '
         'which images are arrayed on the grid (default: "zigzag_horizontal")')

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaconfig.call)
