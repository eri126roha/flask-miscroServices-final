from . import db

class Reservation(db.Model):
    __tablename__ = 'reservations'

    id = db.Column(db.Integer, primary_key=True)
    salle_id = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default=True)  # ✅ ajout d'une valeur par défaut (optionnel)

    def to_dict(self):
        return {
            'id': self.id,
            'salle_id': self.salle_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'user_id': self.user_id,
            'status': self.status
        }
