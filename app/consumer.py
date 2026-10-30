import asyncio
import logging

from app.messaging import app, broker, publish_outbox_forever

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@app.on_startup
async def start_outbox_publisher() -> None:
    asyncio.create_task(publish_outbox_forever())


if __name__ == "__main__":
    import asyncio as _asyncio
    _asyncio.run(app.run())
