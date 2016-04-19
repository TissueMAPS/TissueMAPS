import functools

from flask import request
from flask.ext.jwt import current_identity

from tmaps.extensions import db
from tmaps.error import (
    MalformedRequestError,
    ResourceNotFoundError,
    NotAuthorizedError
)


def get(model_cls, check_ownership=False):
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            # NOTE: This assumes a certain naiming convention!
            model_arg = model_cls.__tablename__[:-1]
            model_id_arg = model_arg + '_id'
            url_args = request.url_rule.arguments
            if model_id_arg in url_args:
                model_id = request.view_args.get(model_id_arg)
                if model_id is None:
                    raise MalformedRequestError()
                obj = db.session.query(model_cls).get_with_hash(model_id)
                kwargs.update({
                    model_arg: obj
                })
                if obj is None:
                    raise ResourceNotFoundError(
                        'The resource of type %s with id "%s" was not found.' % (
                            model_cls.__name__,
                            model_id
                        )
                    )
                if check_ownership:
                    if not obj.belongs_to(current_identity):
                        raise NotAuthorizedError(
                            'This user is not authorized to access the '
                            'resource of type %s with id "%s".' % (
                                model_cls.__name__,
                                model_id
                            )
                        )
                del kwargs[model_id_arg]
            return f(*args, **kwargs)
        return wrapped
    return decorator
