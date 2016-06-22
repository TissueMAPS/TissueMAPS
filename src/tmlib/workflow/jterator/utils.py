import os


def get_module_directories(repo_dir):
    '''Gets the directories were module source code files are located.

    Parameters
    ----------
    repo_dir: str
        value of the "lib" key in the pipeline descriptor file

    Returns
    -------
    Dict[str, str]
        paths to module directories for each language relative to the
        repository directory
    '''
    dirs = {
        'Python': 'src/python/jtmodules',
        'Matlab': 'src/matlab/+jtmodules',
        'R': 'src/r/jtmodules'
    }
    return {k: os.path.join(repo_dir, v) for k, v in dirs.iteritems()}


def complete_path(input_path, step_location):
    '''Completes a relative path.

    Parameters
    ----------
    input_path: str
        relative path the should be completed
    step_location: str
        absolute path to project folder

    Returns
    -------
    str
        absolute path
    '''
    if not input_path:
        return input_path
    else:
        input_path = os.path.expandvars(input_path)
        input_path = os.path.expanduser(input_path)
        if not os.path.isabs(input_path):
            input_path = os.path.join(step_location, input_path)
        return input_path


def get_module_path(module_file, repo_dir):
    '''Gets the absolute path to a module file.

    Parameters
    ----------
    module_file: str
        name of the module file
    repo_dir: str
        absolute path to the local copy of the `jtlib` repository

    Returns
    -------
    str
        absolute path to module file
    '''
    language = determine_language(module_file)
    modules_dir = get_module_directories(repo_dir)[language]
    return os.path.join(modules_dir, module_file)


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
    suffix = os.path.splitext(filename)[1]
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
