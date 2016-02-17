'''
Parse arguments from the command line.
'''

from .cli import Metaextract
from .args import MetaextractInitArgs


parser, subparsers = Metaextract.get_parser_and_subparsers(
    methods={'init', 'submit', 'collect', 'cleanup', 'log', 'info'})

parser.description = '''
        Extract OMEXML metadata from heterogeneous microscopic image file
        formats using Bio-Formats.
    '''

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
MetaextractInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaextract.call)
