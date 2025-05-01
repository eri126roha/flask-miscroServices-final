# kafka_consumer.py
from kafka import KafkaConsumer
import json

from Models import db
from sqlalchemy import cast , String
from Models.reservatio_model import Reservation

def start_kafka_consumer():
    # 🚀 On ouvre le contexte Flask pour pouvoir utiliser db.session
    from app import app
    with app.app_context():
        consumer = KafkaConsumer(
            'reservation',                      # on écoute le topic "salle"
            bootstrap_servers='kafka:29092',
            group_id='reservation-service-group',
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        print("✅ Kafka consumer started and listening to 'salle' topic...")

        for message in consumer:
            event      = message.value
            event_type = event.get("type")
            data       = event.get("data", {})
            print( event_type)

            print(f"📨 Received event: {event_type}")
            print(f"🧾 Payload: {data}")

            # ─── Supprimer toutes les réservations liées au salle_id ─────────────
            if event_type == "salle.deleted":
                salle_id = data.get("salle_id")
                if salle_id is None:
                    print("⚠️  'salle_id' missing in delete event payload.")
                    continue

                try:
                    deleted_count = Reservation.query.filter_by(salle_id=cast(salle_id, String)).delete()
                    db.session.commit()
                    print(f"🗑️  Deleted {deleted_count} reservations for salle_id={salle_id}")
                except Exception as e:
                    db.session.rollback()
                    print(f"❌ Error deleting reservations for salle_id={salle_id}: {e}")

            else:
                print("⚠️  Event type not handled by this consumer, ignoring.")
