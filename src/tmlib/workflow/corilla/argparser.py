'''
Parse arguments from the command line.
'''

from tmlib.workflow.corilla.cli import Corilla
from tmlib.workflow.corilla.args import CorillaInitArgs

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

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(call=Corilla.call)
