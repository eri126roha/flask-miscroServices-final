# kafka_producer.py
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='kafka:29092',  # ou ton IP/domaine si nécessaire
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_reservation_event(event_type,  salle_id, reservation_id, start_date, end_date):
    topic = "salle"
    message = {
        "type": f"reservation.{event_type}",
        "data": {
            "salle_id": salle_id,
            "reservation_id": reservation_id,
            "start_date": start_date,
            "end_date": end_date
        }}
    producer.send(topic, message)
    producer.flush()
