import json
import logging

import redis

from app.core.config import settings


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    channel = f"{settings.redis_channel_prefix.rstrip(':')}:org:1"
    client = redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password or None,
        decode_responses=True,
    )
    pubsub = client.pubsub()
    pubsub.subscribe(channel)
    logger.info("Subscribed to %s", channel)

    try:
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                print(json.dumps(json.loads(message["data"]), indent=2), flush=True)
            except (TypeError, json.JSONDecodeError):
                logger.warning("Received non-JSON Redis message")
    except KeyboardInterrupt:
        logger.info("Stopping Redis subscriber")
    finally:
        pubsub.close()
        client.close()


if __name__ == "__main__":
    main()