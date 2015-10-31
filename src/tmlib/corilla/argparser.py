'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Corilla
from .args import CorillaInitArgs

parser, subparsers = Corilla.get_parser_and_subparsers(
    required_subparsers=['init', 'run', 'submit', 'apply', 'cleanup'])

parser.description = '''
    Calculate illumination statistics over a set of images of the same
    channel, which can then subsequently be applied to individual images for
    CORrection of ILLumination Artifacts.
'''
parser.version = __version__

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional program-specific arguments')
CorillaInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Corilla.call)
