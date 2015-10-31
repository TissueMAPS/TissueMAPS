'''
Arguments of the command line program.
'''

from . import __version__
from .cli import Jterator
from .args import JteratorInitArgs
from .args import JteratorRunArgs
from .args import JteratorCreateArgs
from ..args import CheckArgs
from ..args import CreateArgs
from ..args import RemoveArgs


parser, subparsers = Jterator.get_parser_and_subparsers(
    required_subparsers=[
        'init', 'run', 'submit', 'collect', 'cleanup'
    ])

parser.description = '''
    Image analysis pipeline engine for applying a sequence of algorithms
    to a set of images, for example for segmentation and feature extraction.
'''
parser.version = __version__
parser.add_argument(
    '-p', '--pipeline', type=str, required=True,
    help='name of a pipeline that should be processed')

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional program-specific arguments')
JteratorInitArgs().add_to_argparser(init_extra_group)

run_parser = subparsers.choices['run']
run_extra_group = run_parser.add_argument_group(
    'additional program-specific arguments')
JteratorRunArgs().add_to_argparser(run_extra_group)

create_parser = subparsers.add_parser(
    'create', help='create a new project')
create_parser.description = '''
    Create a new jterator project on disk.
'''
CreateArgs().add_to_argparser(create_parser)
JteratorCreateArgs().add_to_argparser(create_parser)

remove_parser = subparsers.add_parser(
    'remove', help='remove an existing project')
remove_parser.description = '''
    Remove an existing jterator project on disk.\n
    WARNING: This will also remove any project related data!
'''
RemoveArgs().add_to_argparser(remove_parser)

check_parser = subparsers.add_parser(
    'check', help='check descriptor files')
check_parser.description = '''
    Check content of the .pipe and .handles files descriptor files.
'''
CheckArgs().add_to_argparser(check_parser)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Jterator.call)
