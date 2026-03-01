import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s %(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN.get_secret_value())

if settings.REDIS_URL:
    redis = Redis.from_url(settings.REDIS_URL)
    logger.info("FSM storage: Redis (%s)", settings.REDIS_URL)
    dp = Dispatcher(storage=RedisStorage(redis=redis))
else:
    redis = None
    logger.warning("FSM storage: MemoryStorage (REDIS_URL is not set)")
    dp = Dispatcher(storage=MemoryStorage())
