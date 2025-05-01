from . import db
from datetime import datetime
class Salle_time(db.Model):
    __tablename__ = 'Salle_time'
    id = db.Column(db.Integer, primary_key=True)
    salle_id = db.Column(db.Integer, db.ForeignKey('salles.id', ondelete='CASCADE'), nullable=False)
    reservation_id = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return (f"<ReservationTime salle_id={self.salle_id}, "
                f"reservation_id={self.reservation_id}, "
                f"from={self.start_date}, to={self.end_date}>")

    def to_dict(self):
        return {
            'id': self.id,
            'salle_id': self.salle_id,
            'reservation_id': self.reservation_id,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None
        }