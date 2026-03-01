from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import ConnectionError as RedisConnectionError

from config import settings
from db.db_helper import db_helper
from db.models import Base
from loader import bot, dp, logger, redis
from routers import start_router

PROCESSED_UPDATES_LIMIT = 5000
_processed_update_ids_queue: deque[int] = deque(maxlen=PROCESSED_UPDATES_LIMIT)
_processed_update_ids: set[int] = set()

async def init_db():
    async with db_helper.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    dp.include_router(start_router)
    await init_db()

    webhook_url = settings.BASE_URL + "/farma/webhook"
    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.SECRET_TG_KEY,
        drop_pending_updates=True,
    )
    logger.info("Webhook set to: %s", webhook_url)

    yield

    await dp.storage.close()
    if redis is not None:
        await redis.aclose()
    await bot.delete_webhook()
    logger.info("Webhook deleted")


app = FastAPI(lifespan=lifespan)


@app.post("/farma/webhook")
async def handle_telegram_webhook(request: Request):
    try:
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token != settings.SECRET_TG_KEY:
            logger.warning("Invalid Telegram webhook secret token")
            return JSONResponse({"status": "forbidden"}, status_code=403)

        update_data = await request.json()
        from aiogram.types import Update

        update = Update.model_validate(update_data)

        if update.update_id in _processed_update_ids:
            logger.info("Duplicate update skipped: %s", update.update_id)
            return {"status": "ok"}

        if len(_processed_update_ids_queue) == PROCESSED_UPDATES_LIMIT:
            stale_update_id = _processed_update_ids_queue.popleft()
            _processed_update_ids.discard(stale_update_id)

        _processed_update_ids_queue.append(update.update_id)
        _processed_update_ids.add(update.update_id)

        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except RedisConnectionError as exc:
        logger.error("Redis is unavailable while processing update: %s", exc)
        return {"status": "degraded"}
    except Exception as exc:
        logger.error("Telegram webhook error: %s", exc, exc_info=True)
        return JSONResponse({"status": "error"}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, log_level="info")
