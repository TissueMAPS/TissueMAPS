import functools

from flask import request, current_app
from flask.ext.jwt import current_identity

import tmlib.models as tm

from tmserver.model import decode_pk
from tmserver.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError,
    MissingGETParameterError,
    MissingPOSTParameterError
)


def assert_request_params(*params):
    """A decorator for GET and POST request functions that asserts that the
    request contains the required parameters. For GET method the parameters
    are expected to be encoded in the URL, while for POST method they are
    expected in the request body.

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


def decode_body_ids(*model_ids):
    """A decorator that extracts and decodes specified model ids from the POST
    body and inserts them into the argument list of the view function.

    Parameters
    ----------
    model_ids: *str
        encoded model ids

    Returns
    -------
    The wrapped view function.

    Raises
    ------
    MalformedRequestError
        This exception is raised if an id was missing from the request body.

    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            data = request.get_json()
            if not data:
                raise MalformedRequestError(
                    'There was no POST body even though the view was expected '
                    'to receive one.'
                )
            for mid in model_ids:
                if mid not in data.keys():
                    raise MalformedRequestError(
                        'ID "%s" was not in the POST body even though '
                        'the view was expected to receive it.' % mid
                    )
                if not mid.endswith('_id'):
                    raise MalformedRequestError('IDs must end with "_id".')
                encoded_model_id = data.get(mid)
                model_id = decode_pk(encoded_model_id)
                kwargs[mid] = model_id
            return f(*args, **kwargs)
        return wrapped
    return decorator


def decode_url_ids():
    """A decorator that extracts and decodes all model IDs from the URL
    and inserts them into the argument list of the view function.

    Returns
    -------
    The wrapped view function.

    Raises
    ------
    MalformedRequestError
        when ``"experiment_id"`` was missing from the URL
    NotAuthorizedError
        when requested `experiment` does not belong to the user

    """
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            url_args = request.url_rule.arguments
            if 'experiment_id' not in url_args:
                raise MalformedRequestError(
                    'ID "experiment_id" was not in the URL even though '
                    'the view was expected to receive it.'
                )

            for arg in url_args:
                if arg.endswith('_id'):
                    encoded_model_id = request.view_args.get(arg)
                    model_id = decode_pk(encoded_model_id)
                    kwargs[arg] = model_id
                if arg == 'experiment_id':
                    with tm.utils.MainSession() as session:
                        experiment = session.query(tm.ExperimentReference).\
                            get(model_id)
                        try:
                            if not experiment.belongs_to(current_identity):
                                raise NotAuthorizedError(
                                    'User is not authorized to access '
                                    'experiment #%d.' % model_id
                                )
                                current_identity.id
                        except AttributeError:
                            pass
            return f(*args, **kwargs)
        return wrapped
    return decorator
