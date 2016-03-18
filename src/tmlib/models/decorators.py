import os
import os.path as p
import shutil

from sqlalchemy import event


def auto_remove_directory(get_location_func):
    """
    @auto_remove_directory(lambda target: target.location)
    SomeClassWithADirectoryOnDisk(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_delete_callback(mapper, connection, target):
            loc = get_location_func(target)
            shutil.rmtree(loc)

        event.listen(cls, 'after_delete', after_delete_callback)
        return cls
    return class_decorator


def auto_create_directory(get_location_func):
    """
    @auto_create_directory(lambda target: target.location)
    SomeClassWithADirectoryOnDisk(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            loc = get_location_func(target)
            if not p.exists(loc):
                os.mkdir(loc)
            else:
                print (
                    'WARNING: Tried to create location %s '
                    'but it exists already!' % loc
                )
        event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator


def exec_func_after_insert(func):
    """
    @exec_func_after_insert(lambda target: do_something())
    SomeClass(db.Model):
    ...

    """
    def class_decorator(cls):
        def after_insert_callback(mapper, connection, target):
            func(mapper, connection, target)
        event.listen(cls, 'after_insert', after_insert_callback)
        return cls
    return class_decorator
