import json
import redis
from threading import Thread

class EventBus:
    def __init__(self, host="localhost", port=6379):
        self.redis = redis.Redis(host=host, port=port, decode_responses=True)

    def publish(self, event_type: str, data: dict):
        payload = json.dumps({"type": event_type, "data": data})
        self.redis.publish("events", payload)

    def subscribe(self, callback):
        pubsub = self.redis.pubsub()
        pubsub.subscribe("events")

        def run():
            for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    callback(payload)

        Thread(target=run, daemon=True).start()


bus = EventBus()

# Подписка
def handle_event(payload):
    print(f"Получено событие: {payload['type']} -> {payload['data']}")

bus.subscribe(handle_event)

# Публикация
bus.publish("trip.created", {"tripId": 123, "userId": 456})
bus.publish("payment.success", {"amount": 100, "currency": "USD"})
