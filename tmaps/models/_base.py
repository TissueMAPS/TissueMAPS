from tmaps.extensions.encrypt import decode, encode
from tmaps.extensions.database import db

class CRUDMixin(object):
    """Mixin that adds convenience methods for CRUD (create, read, update, delete)
    operations.
    """

    @classmethod
    def create(cls, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save()

    def update(self, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.iteritems():
            setattr(self, attr, value)
        return commit and self.save() or self

    def save(self, commit=True):
        """Save the record."""
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        """Remove the record from the database."""
        db.session.delete(self)
        return commit and db.session.commit()


class Model(db.Model):

    __abstract__ = True

    @classmethod
    def get(cls, id):
        return cls.query.get(id)


class HashIdModel(Model):

    __abstract__ = True

    @property
    def hash(self):
        return encode(self.id)

    @classmethod
    def get(cls, id):
        if type(id) == unicode or type(id) == str:
            decoded_id = decode(id)
        elif type(id) == int:
            decoded_id = id
        else:
            raise ValueError('Cannot handle type of id: ' + str(type(id)))

        return super(HashIdModel, cls).get(decoded_id)
