from kafka import KafkaConsumer
import json
from datetime import datetime

from Models import db
from Models.salle_time import Salle_time


def handle_salle_event(event_type, data):
    """
    Handle creation and deletion of Salle_time entries based on Kafka events.
    """
    print(f"📨 Event received on topic 'salle': {event_type}")
    print(f"🧾 Payload: {data}")

    if event_type == "reservation.created":
        # Create a new Salle_time entry
        try:
            st = Salle_time(
                salle_id=data["salle_id"],
                reservation_id=data["reservation_id"],
                start_date=datetime.fromisoformat(data["start_date"]),
                end_date=datetime.fromisoformat(data["end_date"])
            )
            db.session.add(st)
            db.session.commit()
            print(f"✅ Salle_time created for reservation_id={st.reservation_id}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating Salle_time: {e}")

    elif event_type == "reservation.deleted":
        # Delete the Salle_time entry for the given reservation_id
        reservation_id = data.get("reservation_id")
        if reservation_id is None:
            print("⚠️ reservation_id missing in event data.")
            return

        try:
            st = Salle_time.query.filter_by(reservation_id=reservation_id).first()
            if st:
                db.session.delete(st)
                db.session.commit()
                print(f"🗑️ Salle_time deleted for reservation_id={reservation_id}")
            else:
                print(f"⚠️ No Salle_time found for reservation_id={reservation_id}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting Salle_time: {e}")

    else:
        print("⚠️ Unrecognized event type. Ignoring.")


def start_salle_consumer():
    # Import the Flask app inside the function to avoid circular imports
    from app import app

    consumer = KafkaConsumer(
        'salle',
        bootstrap_servers='kafka:29092',
        group_id='salle-service-group',
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )

    print("🎧 Kafka consumer listening on topic: 'salle'")

    for message in consumer:
        event_type = message.value.get("type")
        data = message.value.get("data", {})

        # Push Flask app context for DB operations
        with app.app_context():
            handle_salle_event(event_type, data)


if __name__ == "__main__":
    start_salle_consumer()
