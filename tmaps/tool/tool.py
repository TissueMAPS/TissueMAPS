from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, HashIdModel
from tmaps.model.decorators import auto_generate_hash 


@auto_generate_hash
class Tool(HashIdModel, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(20))
    name = db.Column(db.String(120))
    icon = db.Column(db.String(120))
    description = db.Column(db.Text)
    full_class_path = db.Column(db.String(120))

    def get_class(self):
        def import_from_str(name):
            components = name.split('.')
            mod = __import__(components[0])
            for comp in components[1:]:
                mod = getattr(mod, comp)
            return mod
        cls = import_from_str(self.full_class_path)
        return cls

    def to_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'icon': self.icon
        }
