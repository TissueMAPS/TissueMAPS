'''
Parse arguments from the command line.
'''

from .cli import Jterator
from .args import JteratorInitArgs
from .args import JteratorRunArgs
from .args import JteratorCreateArgs
from .args import JteratorSubmitArgs
from .args import JteratorCollectArgs
from .args import JteratorResubmitArgs
from .args import JteratorLogArgs
from .args import JteratorInfoArgs
from .args import JteratorCheckArgs
from .args import JteratorRemoveArgs
from ..args import CheckArgs
from ..args import CreateArgs
from ..args import RemoveArgs


parser, subparsers = Jterator.get_parser_and_subparsers()

parser.description = '''
    Image analysis pipeline engine for applying a sequence of algorithms
    to a set of images, for example for segmentation and feature extraction.
'''

# All subparsers require the extra argument "pipeline"

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
JteratorInitArgs().add_to_argparser(init_extra_group)

run_parser = subparsers.choices['run']
run_extra_group = run_parser.add_argument_group(
    'additional step-specific arguments')
JteratorRunArgs().add_to_argparser(run_extra_group)

collect_parser = subparsers.choices['collect']
collect_extra_group = collect_parser.add_argument_group(
    'additional step-specific arguments')
JteratorCollectArgs().add_to_argparser(collect_extra_group)

resubmit_parser = subparsers.choices['resubmit']
resubmit_extra_group = resubmit_parser.add_argument_group(
    'additional step-specific arguments')
JteratorResubmitArgs().add_to_argparser(resubmit_extra_group)

submit_parser = subparsers.choices['submit']
submit_extra_group = submit_parser.add_argument_group(
    'additional step-specific arguments')
JteratorSubmitArgs().add_to_argparser(submit_extra_group)

log_parser = subparsers.choices['log']
log_extra_group = log_parser.add_argument_group(
    'additional step-specific arguments')
JteratorLogArgs().add_to_argparser(log_extra_group)

info_parser = subparsers.choices['info']
info_extra_group = info_parser.add_argument_group(
    'additional step-specific arguments')
JteratorInfoArgs().add_to_argparser(info_extra_group)

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
JteratorRemoveArgs().add_to_argparser(remove_parser)

check_parser = subparsers.add_parser(
    'check', help='check descriptor files')
check_parser.description = '''
    Check content of the .pipe and .handles files descriptor files.
'''
CheckArgs().add_to_argparser(check_parser)
JteratorCheckArgs().add_to_argparser(check_parser)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Jterator.call)
