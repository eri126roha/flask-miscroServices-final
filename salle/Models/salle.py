from datetime import datetime
from . import db

class Salle(db.Model):
    __tablename__ = 'salles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    times = db.relationship("Salle_time", backref="salle", passive_deletes=True)

    def __repr__(self):
        return f"<Salle {self.name}, capacity={self.capacity}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'capacity': self.capacity
        }