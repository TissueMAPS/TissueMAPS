from tmaps.extensions.database import db
from tmaps.model import CRUDMixin, Model
from tmaps.model.decorators import auto_generate_hash 


@auto_generate_hash
class Tool(Model, CRUDMixin):
    id = db.Column(db.Integer, primary_key=True)
    hash = db.Column(db.String(20))
    name = db.Column(db.String(120))
    icon = db.Column(db.String(120))
    description = db.Column(db.Text)
    full_class_path = db.Column(db.String(120))

    def to_dict(self):
        return {
            'id': self.hash,
            'name': self.name,
            'description': self.description,
            'icon': self.icon
        }
