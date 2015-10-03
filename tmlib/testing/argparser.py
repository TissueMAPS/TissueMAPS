import argparse

parser = argparse.ArgumentParser()
parser.description = '''
    Command line interface for testing.
'''
parser.add_argument(
    '-v', '--verbosity', dest='verbosity', action='count', default=0,
    help='increase logging verbosity to DEBUG (default: WARN)')
