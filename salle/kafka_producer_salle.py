from kafka import KafkaProducer
import json

# Initialisation du producteur Kafka
producer = KafkaProducer(
    bootstrap_servers='kafka:29092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_reservation_event(event_type, salle_id):
    """
    Envoie un événement Kafka (created ou deleted) dans le topic 'reservation'.
    Payload = { salle_id: ... }
    """
    topic = "reservation"
    message = {
        "type": f"salle.{event_type}",  # "reservation.created" ou "reservation.deleted"
        "data": {
            "salle_id": salle_id
        }
    }

    try:
        producer.send(topic, message)
        producer.flush()
        print(f"✅ Event sent to topic '{topic}': {message}")
    except Exception as e:
        print(f"❌ Failed to send Kafka event: {e}")
