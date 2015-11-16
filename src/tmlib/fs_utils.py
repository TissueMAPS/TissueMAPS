'''
Utility functions for file system operations.
'''
import os


class CTError(Exception):
    def __init__(self, errors):
        self.errors = errors

try:
    O_BINARY = os.O_BINARY
except:
    O_BINARY = 0
READ_FLAGS = os.O_RDONLY | O_BINARY
WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | O_BINARY
BUFFER_SIZE = 128*1024


def fast_copyfile(src, dst):
    '''
    Copy file from `src` to `dst`.

    Parameters
    ----------
    src: str
        absolute path to source file
    dst: str
        absolute path to destination file

    Note
    ----
    Code was adapted from stack-overflow question 22078621.
    '''
    try:
        fin = os.open(src, READ_FLAGS)
        stat = os.fstat(fin)
        fout = os.open(dst, WRITE_FLAGS, stat.st_mode)
        for x in iter(lambda: os.read(fin, BUFFER_SIZE), ""):
            os.write(fout, x)
    finally:
        try:
            os.close(fin)
        except:
            pass
        try:
            os.close(fout)
        except:
            pass


def fast_copytree(src, dst, symlinks=False, ignore=[]):
    '''
    Copy files from `src` to `dst`.

    Parameters
    ----------
    src: str
        absolute path to source directory
    dst: str
        absolute path to destination directory
    symlinks: bool, optional
        also copy symlinks (default: ``False``)
    ignore: List[str]
        names of files that should be ignored (default: ``list()``)

    Raises
    ------
    tmlib.fs_utils.CTError
        when copying of a file failed

    Note
    ----
    Code was adapted from stack-overflow question 22078621.
    '''
    names = os.listdir(src)

    if not os.path.exists(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignore:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                fast_copytree(srcname, dstname, symlinks, ignore)
            else:
                fast_copytree(srcname, dstname)
            # XXX What about devices, sockets etc.?
        except (IOError, os.error) as err:
            errors.append((srcname, dstname, str(err)))
        except CTError as err:
            errors.extend(err.errors)
    if errors:
        raise CTError(errors)
