from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, KafkaConnectionError
import time

def create_topic():
    max_retries = 3
    retry_delay = 5  # seconds
    print("🔧 Connecting to Kafka...")

    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempt {attempt + 1}: Trying to connect to Kafka...")

            admin_client = KafkaAdminClient(
                bootstrap_servers=['kafka:29092'],
                client_id='python-admin',
                api_version=(7, 8, 0),
                request_timeout_ms=10000
            )

            topic = NewTopic(
                name="reservation",  # 🆕 le nom du topic ici
                num_partitions=1,
                replication_factor=1
            )

            admin_client.create_topics([topic])
            print("✅ Topic 'reservation' created successfully!")
            return

        except TopicAlreadyExistsError:
            print("⚠️ Topic 'reservation' already exists")
            return
        except KafkaConnectionError as e:
            print(f"❌ Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("❌ Failed after multiple retries")
        finally:
            if 'admin_client' in locals():
                admin_client.close()

if __name__ == "__main__":
    create_topic()
