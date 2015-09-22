import os
import re


def complete_path(input_path, project_dir):
    '''
    Complete relative path variables.

    Parameters
    ----------
    input_path: str
        the path the should be completed
    project_dir: str
        absolute path to project folder
    '''
    input_path = os.path.expandvars(input_path)
    input_path = os.path.expanduser(input_path)
    if input_path.startswith('.'):
        input_path = os.path.join(project_dir, input_path)
    return input_path


def complete_module_path(input_path, repo_dir, project_dir):
    '''
    Complete module path, which can be provided in the pipeline descriptor
    file as full path, relative path or a path containing format string.

    Parameters
    ----------
    input_path: str
        the path the should be completed
    repo_dir: str
        value of the "lib" key in the pipeline descriptor file
    project_dir: str
        absolute path to project folder
    '''
    # Replace the `variable` name with the actual value
    if repo_dir and re.search(r'^{lib}', input_path):
        re_path = input_path.format(lib=repo_dir)
    elif not os.path.isabs(input_path):
        re_path = os.path.join(project_dir, input_path)
    else:
        re_path = input_path
    # Expand path containing environment variables '$'
    complete_path = os.path.expandvars(re_path)
    # Expand path starting with `~`
    complete_path = os.path.expanduser(re_path)
    return complete_path


def determine_language(filename):
    '''
    Determine language form module filename suffix.

    Parameters
    ----------
    filename: str
        name of a module file

    Returns
    -------
    str
    '''
    filename = os.path.abspath(filename)  # removes trailing '/'
    suffix = os.path.splitext(os.path.basename(filename))[1]
    if suffix == '.m':
        return 'Matlab'
    elif suffix == '.R' or suffix == '.r':
        return 'R'
    elif suffix == '.py':
        return 'Python'
    elif suffix == '.jl':
        return 'Julia'
    else:
        raise Exception('Language could not be determined from filename.')

