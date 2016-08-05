import functools

from flask import request, current_app
from flask.ext.jwt import current_identity

from tmserver.extensions import db
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError,
    MissingGETParameterError,
    MissingPOSTParameterError
)


def assert_request_params(*params):
    """A decorator for GET and POST request functions that asserts that the
    request contains the required parameters.

    Parameters
    ----------
    *params: List[str]
        names of required parameters

    Raises
    ------
    tmserver.error.MissingPOSTParameterError or tmserver.error.MissingGETParameterError
            when a required parameter is missing in the request
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            if request.method == 'POST':
                data = request.get_json()
            for p in params:
                if request.method == 'GET':
                    if p not in request.args:
                        raise MissingGETParameterError(p)
                elif request.method == 'POST':
                    if data is None:
                        raise MissingPOSTParameterError(p)
                    else:
                        if p not in data:
                            raise MissingPOSTParameterError(p)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def extract_model_from_body(*model_classes, **kw):
    """A decorator that extracts all model ids from a POST body
    and uses them to get the respective objects from the database
    and insert them into the argument list of the view function.

    Parameters
    ----------
    model_classes : *type
        The models for which objects should be queried.

    Returns
    -------
    The wrapped view function.

    Raises
    ------
    MalformedRequestError
        This exception is raised if an id was missing from the request body.

    ResourceNotFoundError
        This exception is raised if no object with a request id was found.

    NotAuthorizedError
        This exception is raised if the queried object does not belong to the
        user. For this to work `check_ownership` has to be True and the object
        has to have a `belongs_to(user: User)` method.

    """
    check_ownership = kw.get('check_ownership', False)

    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            data = request.get_json()
            if not data:
                err = (
                    'There was no POST body even though the view was expected '
                    'to receive one!'
                )
                raise MalformedRequestError(err)
            # Constructor a dictionary that maps id keys to models, e.g.
            # { 'experiment_id': Experiment, 'plate_id': Plate }
            key_model_map = dict(
                [(m.__name__.lower() + '_id', m) for m in model_classes])
            # Check for each key in the POST request body if such a key it
            # corresponds to one of the model keys
            # (e.g. "experiment_id" if Experiment was passed to the decorator)
            for key in data:
                if key not in key_model_map:
                    continue
                # Check if the id was supplied
                id = data[key]
                if id is None:
                    raise MalformedRequestError(
                        'No value supplied for key "%s".' % key
                    )
                # Try to get the object with this id from the DB
                model_cls = key_model_map[key]
                obj = db.session.query(model_cls).get_with_hash(id)
                if obj is None:
                    raise ResourceNotFoundError(model_cls.__name__)
                # Optionally check if the user has access to this object
                if check_ownership:
                    if not obj.belongs_to(current_identity):
                        raise NotAuthorizedError(
                            'This user is not authorized to access the '
                            'resource of type %s with id "%s".' % (
                                model_cls.__name__,
                                id
                            )
                        )
                # The object was queried correctly, remove from map
                del key_model_map[key]
                kwargs[model_cls.__name__.lower()] = obj

            # Lastly check if any of the id-keys were missing from the
            # request body
            remaining_model_keys = key_model_map.keys()
            if remaining_model_keys:
                raise MalformedRequestError(
                    'A request to this endpoint needs to provide the keys: '
                    ', '.join(['"%s"' % k for k in remaining_model_keys])
                )
            return f(*args, **kwargs)
        return wrapped
    return decorator


def extract_model_from_path(*model_classes, **kw):
    """A decorator that extracts all model ids from a URL
    and uses them to get the respective objects from the database
    and insert them into the argument list of the view function.

    Parameters
    ----------
    model_classes : *type
        The models for which objects should be queried.

    Returns
    -------
    The wrapped view function.

    Raises
    ------
    MalformedRequestError
        This exception is raised if an id was missing from the request body.

    ResourceNotFoundError
        This exception is raised if no object with a request id was found.

    NotAuthorizedError
        This exception is raised if the queried object does not belong to the
        user. For this to work `check_ownership` has to be True and the object
        has to have a `belongs_to(user: User)` method.

    """
    check_ownership = kw.get('check_ownership', False)

    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # NOTE: This assumes a certain naiming convention!
            for model_cls in model_classes:
                model_arg = model_cls.__tablename__[:-1]
                model_id_arg = model_arg + '_id'
                url_args = request.url_rule.arguments
                if model_id_arg in url_args:
                    model_id = request.view_args.get(model_id_arg)
                    if model_id is None:
                        raise MalformedRequestError()
                    if model_id == 'undefined':
                        raise ValueError(
                            'ID for model "%s" not defined' % model_cls.__name__
                        )
                    obj = db.session.query(model_cls).get_with_hash(model_id)
                    kwargs.update({
                        model_arg: obj
                    })
                    if obj is None:
                        raise ResourceNotFoundError(model_cls.__name__)
                    if check_ownership:
                        if not obj.belongs_to(current_identity):
                            raise NotAuthorizedError(
                                'This user is not authorized to access the '
                                'resource of type %s with id "%s".' % (
                                    model_cls.__name__, model_id
                                )
                            )
                    del kwargs[model_id_arg]
            return f(*args, **kwargs)
        return wrapped
    return decorator
