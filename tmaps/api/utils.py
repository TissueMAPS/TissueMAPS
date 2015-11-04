class ModelAccessFailed(Exception):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return str(self.response)


class APIModelAccessor(object):
    """
    try:
        obj = APIModelAccessor(Experiment).get(some_id)
    except ModelAccessFailed as e:
        return e.response
    else:
        # do something with obj


    or with automatic user checking:

    try:
        obj = APIModelAccessor(Experiment).get_with_usr(some_id, some_user)
    except ModelAccessFailed as e:
        return e.response
    else:
        # do something with obj
    """
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def get(self, id):
        obj = self.model_cls.get_by_id(id)
        if obj is None:
            raise ModelAccessFailed(
                'Error: not able to find object of class %s'
                % self.model_cls.__name__, 404
            )
        else:
            return obj

    def get_with_user(self, id, user):
        try:
            obj = self.get(id)
        except ModelAccessFailed as e:
            raise e
        else:
            if not obj.belongs_to(user):
                raise ModelAccessFailed(
                    'Error: this user does not have the rights to '
                    'acccess this ressource',
                    401
                )
            else:
                return obj
