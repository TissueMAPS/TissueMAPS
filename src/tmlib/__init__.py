import os
import glob

from tmlib.version import __version__


def get_cli_tools():
    '''Lists implemented command line interfaces (cli).

    Returns
    -------
    List[str]
        names of cli tools
    '''
    root = os.path.join(os.path.dirname(__file__), 'workflow')
    def _is_package(d):
        # A step is defined as a subpackage that implements the following
        # modules: api, cli, args
        d = os.path.join(root, d)
        return(
            os.path.isdir(d) and
            glob.glob(os.path.join(d, '__init__.py')) and
            glob.glob(os.path.join(d, 'api.py')) and
            glob.glob(os.path.join(d, 'cli.py')) and
            glob.glob(os.path.join(d, 'args.py'))
        )

    return filter(_is_package, os.listdir(root))

