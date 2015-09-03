import argparse
from . import __version__
from .cli import MetaExtract


parser = argparse.ArgumentParser(
    description='''
        Extract images from heterogeneous file formats
        using the Bio-Formats library.
    ''')
parser.add_argument('--version', action='version',
                    version='%(prog)s ' + __version__, help='Display version')
parser.add_argument('-c', '--cfg', dest='cfg_file', type=str, default=None,
                    help='path to custom YAML configuration file')

subparsers = parser.add_subparsers(dest='name')

parser_joblist = subparsers.add_parser(
    'joblist',
    description='''
        Create a list of job descriptions (batches) for parallel
        processing, print it to standard output, and write it to a file
        on disk in YAML format.
    ''')
parser_joblist.add_argument('-b', '--batch_size', dest='batch_size',
                            type=int, default=5,
                            help='number of image files that should \
                                  be processed per job (default: 5)')
parser_joblist.add_argument('cycle_dir', help='path to cycle directory')
parser_joblist.set_defaults(handler=MetaExtract.call)

parser_submit = subparsers.add_parser(
    'submit',
    description='''
        Submit jobs to the cluster and monitor their processing.
    ''')
parser_submit.add_argument('--no_shared_network',
                           dest='shared_network', action='store_false',
                           help='in case worker nodes don\'t have \
                                 access to a shared network')
parser_submit.add_argument('cycle_dir', help='path to cycle directory')
parser_submit.set_defaults(handler=MetaExtract.call)

parser_collect = subparsers.add_parser(
    'collect',
    description='''
        Collect the output, i.e. copy the standard output to .ome.xml
        files.
    ''')
parser_collect.add_argument('cycle_dir', help='path to cycle directory')
parser_collect.set_defaults(handler=MetaExtract.call)
