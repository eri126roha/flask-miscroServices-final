from flask import Flask,jsonify,request
from Models.salle import Salle
from Models import db
from datetime import datetime
from Models.salle_time import Salle_time
from kafka_producer_salle import (producer,send_reservation_event)
from threading import Thread
from kafka_consumer_salle import start_salle_consumer
app=Flask(__name__)
app.secret_key="secret key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ouma:passwordouma@salleDb:5432/salle'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()
@app.route('/api/salles/salles/<int:id>', methods=['GET'])
def get_salle(id):
        salle = Salle.query.get_or_404(id)
        return jsonify(salle.to_dict())
@app.route('/api/salles/salles', methods=['GET'])
def get_salles():
    salles = Salle.query.all()
    return jsonify([salle.to_dict() for salle in salles])
@app.route('/api/salles/salles', methods=['POST'])
def create_salle():
        data = request.get_json()
        name = data.get('name')
        capacity = data.get('capacity')
        if not name or capacity is None:
            return jsonify({'error': 'name and capacity are required'}), 400
        salle = Salle(name=name, capacity=capacity)
        db.session.add(salle)
        db.session.commit()
        return jsonify(salle.to_dict()), 201

@app.route('/api/salles/salles/<int:id>', methods=['PUT'])
def update_salle(id):
        salle = Salle.query.get_or_404(id)
        data = request.get_json()
        salle.name = data.get('name', salle.name)
        salle.capacity = data.get('capacity', salle.capacity)
        db.session.commit()
        return jsonify(salle.to_dict())

@app.route('/api/salles/salles/<int:id>', methods=['DELETE'])
def delete_salle(id):
    salle = Salle.query.get_or_404(id)
    db.session.delete(salle)
    db.session.commit()
    send_reservation_event(
        event_type="deleted",
        salle_id=salle.id
    )

    return jsonify({'message': 'Salle supprimée avec succès'})
#tested
@app.route('/api/salles/salle_time/intersect', methods=['GET'])
def check_salle_time_overlap():
    # Récupère les paramètres ISO8601 (ex. “2025‑04‑22T10:00:00”)
    start_str = request.args.get('start_date')
    end_str   = request.args.get('end_date')
    if not start_str or not end_str:
        return jsonify({'error': 'start_date et end_date sont requis'}), 400
    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt   = datetime.fromisoformat(end_str)
    except ValueError:
        return jsonify({'error': 'Format de date invalide, utilisez ISO8601'}), 400

    exists_overlap = (
        Salle_time.query
            .filter(Salle_time.start_date <= end_dt,
                    Salle_time.end_date   >= start_dt)
            .first() is not None
    )
    return jsonify(exists_overlap)
#tested
@app.route('/api/salles/salle_time', methods=['POST'])
def create_salle_time():
    data = request.get_json() or {}
    salle_id       = data.get('salle_id')
    reservation_id = data.get('reservation_id')
    start_str      = data.get('start_date')
    end_str        = data.get('end_date')

    # Vérification des paramètres requis
    if not all([salle_id, reservation_id, start_str, end_str]):
        return jsonify({'error': 'salle_id, reservation_id, start_date et end_date sont requis'}), 400

    try:
        start_dt = datetime.fromisoformat(start_str)
        end_dt   = datetime.fromisoformat(end_str)
    except ValueError:
        return jsonify({'error': 'Format de date invalide, utilisez ISO8601'}), 400

    record = Salle_time(
        salle_id=salle_id,
        reservation_id=reservation_id,
        start_date=start_dt,
        end_date=end_dt
    )
    db.session.add(record)
    db.session.commit()

    return jsonify(record.to_dict()), 201
@app.route('/api/salles/salle_time/<int:reservation_id>', methods=['DELETE'])
def delete_salle_time_by_reservation_id(reservation_id):
    record = Salle_time.query.filter_by(reservation_id=reservation_id).first()
    if not record:
        return jsonify({'error': 'Aucun enregistrement trouvé avec ce reservation_id'}), 404

    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': f'Enregistrement avec reservation_id {reservation_id} supprimé avec succès'})

if __name__ == '__main__':
    Thread(target=start_salle_consumer, daemon=True).start()

    app.run(host="0.0.0.0",debug=True,port=5000)











