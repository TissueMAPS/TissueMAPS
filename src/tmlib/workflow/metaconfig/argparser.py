'''
Parse arguments from the command line.
'''

from tmlib.workflow.metaconfig.cli import Metaconfig
from tmlib.workflow.metaconfig.args import MetaconfigInitArgs


parser, subparsers = Metaconfig.get_parser_and_subparsers()

parser.description = '''
        Configure metadata based on OMEXML extracted from image files
        and complement it with additionally provided information.
    '''

init_parser = subparsers.choices['init']
init_extra_group = init_parser.add_argument_group(
    'additional step-specific arguments')
MetaconfigInitArgs().add_to_argparser(init_extra_group)

for name in subparsers.choices:
    subparsers.choices[name].set_defaults(handler=Metaconfig.call)
