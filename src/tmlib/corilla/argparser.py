'''
Parse arguments from the command line.
'''

from .cli import Corilla
from .args import CorillaInitArgs
from ..args import ApplyArgs

parser, subparsers = Corilla.get_parser_and_subparsers(
    methods={'init', 'run', 'submit', 'resubmit', 'cleanup', 'log', 'info'})

parser.description = '''
    Calculate illumination statistics over a set of images of the same
    channel, which can then subsequently be applied to individual images for
    CORrection of ILLumination Artifacts.
'''

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
CorillaInitArgs().add_to_argparser(init_extra_group)

apply_parser = subparsers.add_parser(
    'apply', help='apply job output')
apply_parser.description = '''
    Apply calculated shift statistics to (a subset of) images
    in order to align them between cycles.
'''
ApplyArgs().add_to_argparser(apply_parser)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Corilla.call)
