from flask import Flask,jsonify,g,request
from Models import db
from Models.reservatio_model import Reservation
from kafka_producer import (producer,send_reservation_event)
import requests
from datetime import datetime
import jwt
from threading import Thread
from kafka_consumer import start_kafka_consumer
app=Flask(__name__)
app.secret_key="secret key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://reservation:reservation@reservationDb:5432/reservationDb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
ROOM_SERVICE_URL = "http://salle:5000/api/salles/salles"

with app.app_context():
    db.create_all()
@app.before_request
def check_jwt():
    auth_header = request.headers.get('Authorization', None)
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'message': 'Missing or invalid Authorization header'}), 401

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        
        g.user = payload

    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid token'}), 401
@app.route("/api/reservation", methods=["POST"])
def add_reservation():
    data = request.get_json() or {}
    for field in ("salle_id", "start_date", "end_date", "people_count"):
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    salle_id     = data["salle_id"]
    people_count = data["people_count"]
    try:
        start_dt = datetime.fromisoformat(data["start_date"])
        end_dt   = datetime.fromisoformat(data["end_date"])
    except ValueError:
        return jsonify({"error": "Dates must be in ISO format"}), 400

    if start_dt >= end_dt:
        return jsonify({"error": "start_date must be before end_date"}), 400

    try:
        # On transmet le token si besoin :
        headers = {"Authorization": request.headers.get("Authorization", "")}
        resp = requests.get(f"{ROOM_SERVICE_URL}/{salle_id}", headers=headers, timeout=3)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Cannot reach room service", "detail": str(e)}), 502

    if resp.status_code == 404:
        return jsonify({"error": "Salle not found"}), 404
    if resp.status_code != 200:
        return jsonify({"error": "Room service error", "status": resp.status_code}), 502

    # Récupère la capacité retournée par le service
    salle_data = resp.json()
    capacity   = salle_data.get("capacity")
    if capacity is None:
        return jsonify({"error": "Invalid response from room service"}), 502

    if capacity < people_count:
        return jsonify({
            "error": "Salle capacity exceeded",
            "capacity": capacity,
            "requested": people_count
        }), 400

    # ─── Vérification de conflit local (base “reservations”) ───────────────
    conflict = Reservation.query.filter(
        Reservation.salle_id == salle_id,
        Reservation.start_date < end_dt,
        Reservation.end_date   > start_dt,
        Reservation.status == "confirmer"
    ).first()
    if conflict:
        return jsonify({
            "error": "Time slot unavailable",
            "conflict_with": {
                "id": conflict.id,
                "start_date": conflict.start_date.isoformat(),
                "end_date":   conflict.end_date.isoformat()
            }
        }), 409

    # ─── Création de la réservation ─────────────────────────────────────────
    new_res = Reservation(
        salle_id   = salle_id,
        start_date = start_dt,
        end_date   = end_dt,
        user_id    = g.user["user_id"],
        status     = "non_confirmer"
    )
    db.session.add(new_res)
    db.session.commit()

    return jsonify(new_res.to_dict()), 201
@app.route("/api/reservation", methods=["GET"])
def get_reservations():
    # Récupère les filtres éventuels
    salle_id       = request.args.get("salle_id")
    user_id        = request.args.get("user_id")
    start_date_str = request.args.get("start_date")
    end_date_str   = request.args.get("end_date")
    status_str     = request.args.get("status")

    # Base de la requête
    query = Reservation.query

    # Filtre par salle_id en utilisant filter()
    if salle_id:
        query = query.filter(Reservation.salle_id == salle_id)

    # Filtre par user_id en utilisant filter()
    if user_id:
        query = query.filter(Reservation.user_id == user_id)

    # Filtre par status (conversion string → bool)
    if status_str is not None:
        status_bool = status_str.lower() in ("true", "1", "yes")
        query = query.filter(Reservation.status == status_bool)

    # Filtre par date de début
    if start_date_str:
        try:
            start_dt = datetime.fromisoformat(start_date_str)
        except ValueError:
            return jsonify({"error": "start_date must be ISO format"}), 400
        query = query.filter(Reservation.start_date >= start_dt)

    # Filtre par date de fin
    if end_date_str:
        try:
            end_dt = datetime.fromisoformat(end_date_str)
        except ValueError:
            return jsonify({"error": "end_date must be ISO format"}), 400
        query = query.filter(Reservation.end_date <= end_dt)

    # Exécution et sérialisation
    results = query.all()
    return jsonify([r.to_dict() for r in results]), 200
@app.route("/api/reservation/<int:id>", methods=["DELETE"])
def delete_reservation(id):

    reservation = Reservation.query.get(id)
    if not reservation:
        return jsonify({"error": "Reservation not found"}), 404

    user = g.user
    user_id = user.get("user_id")
    role = user.get("role", "user")

    if role != "admin" and reservation.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    

    db.session.delete(reservation)
    db.session.commit()
    # 📤 Emit DELETE event before removal
    send_reservation_event(
        event_type="deleted",
        salle_id=reservation.salle_id,
        reservation_id=reservation.id,
        start_date=reservation.start_date.isoformat(),
        end_date=reservation.end_date.isoformat()
    )
    return jsonify({"message": "Reservation deleted successfully"}), 200


@app.route("/api/reservation/<int:id>", methods=["PUT"])
def modifier_reservation(id):

    reservation = Reservation.query.get(id)
    if not reservation:
        return jsonify({"error": "Reservation not found"}), 404

    user = g.user
    user_id = user.get("user_id")
    role = user.get("role", "user")

    if role != "admin" and reservation.user_id != user_id:
        return jsonify({"error": "Unauthorized"}), 403

    # 🔥 Emit DELETE event for old reservation
    

    data = request.get_json() or {}
    updated_fields = []
    salle_id = reservation.salle_id
    start_date = reservation.start_date
    end_date = reservation.end_date

    if "start_date" in data:
        start_date = datetime.fromisoformat(data["start_date"])
        updated_fields.append("start_date")

    if "end_date" in data:
        end_date = datetime.fromisoformat(data["end_date"])
        updated_fields.append("end_date")

    if "salle_id" in data:
        salle_id = data["salle_id"]
        updated_fields.append("salle_id")

    if start_date >= end_date:
        return jsonify({"error": "start_date must be before end_date"}), 400

    try:
        headers = {"Authorization": request.headers.get("Authorization", "")}
        resp = requests.get(f"{ROOM_SERVICE_URL}/{salle_id}", headers=headers, timeout=3)
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Cannot reach room service", "detail": str(e)}), 502

    if resp.status_code == 404:
        return jsonify({"error": "Salle not found"}), 404
    if resp.status_code != 200:
        return jsonify({"error": "Room service error", "status": resp.status_code}), 502

    salle_data = resp.json()
    capacity = salle_data.get("capacity")
    if capacity is None:
        return jsonify({"error": "Invalid response from room service"}), 502

    conflict = Reservation.query.filter(
        Reservation.id != reservation.id,
        Reservation.salle_id == salle_id,
        Reservation.status == "confirmer",
        Reservation.start_date < end_date,
        Reservation.end_date > start_date
    ).first()
    if conflict:
        return jsonify({
            "error": "Time slot unavailable",
            "conflict_with": {
                "id": conflict.id,
                "start_date": conflict.start_date.isoformat(),
                "end_date": conflict.end_date.isoformat()
            }
        }), 409

    reservation.salle_id = salle_id
    reservation.start_date = start_date
    reservation.end_date = end_date

    if updated_fields:
        reservation.status = "non_confirmer"

    db.session.commit()
    send_reservation_event(
        event_type="deleted",
        salle_id=reservation.salle_id,
        reservation_id=reservation.id,
        start_date=reservation.start_date.isoformat(),
        end_date=reservation.end_date.isoformat()
    )
    return jsonify(reservation.to_dict()), 200


@app.route("/api/reservation/confirme/<int:id>", methods=["PUT"])
def confirme_reservation(id):

    reservation = Reservation.query.get(id)
    if not reservation:
        return jsonify({"error": "Reservation not found"}), 404

    role = g.user.get("role", "user")
    if role != "admin":
        return jsonify({"error": "Only admin can confirm reservations"}), 403

    reservation.status = "confirmer"
    db.session.commit()

    # 🚀 Emit CREATED event after confirming
    send_reservation_event(
        event_type="created",
        salle_id=reservation.salle_id,
        reservation_id=reservation.id,
        start_date=reservation.start_date.isoformat(),
        end_date=reservation.end_date.isoformat()
    )

    return jsonify(reservation.to_dict()), 200


if __name__ == "__main__":
    # 🔁 Start Kafka consumer in background
    Thread(target=start_kafka_consumer, daemon=True).start()

    # 🚀 Start Flask app
    app.run(host="0.0.0.0",debug=True,port=5000)