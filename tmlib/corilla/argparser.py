from . import __version__
from .cli import Corilla


parser, subparsers = Corilla.get_parser_and_subparsers(
                        required_subparsers=[
                            'run', 'joblist', 'submit', 'apply'])

parser.description = '''
        Calculate illumination statistics over a set of images of the same
        channel, which can then be applied to individual images for
        CORrection of ILLumination Artifacts.
    '''
parser.version = __version__

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Corilla.call)
