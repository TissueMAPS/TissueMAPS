'''
Parse arguments from the command line.
'''

from .cli import Imextract
from .args import ImextractInitArgs


parser, subparsers = Imextract.get_parser_and_subparsers(
    methods={'init', 'run', 'submit', 'resubmit', 'cleanup', 'log', 'info'})

parser.description = '''
    Extract images from heterogeneous microscopic image file formats
    and store each 2D plane in a separate PNG file.
'''

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
ImextractInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Imextract.call)
