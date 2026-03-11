import asyncio
import logging

from sqlalchemy import select

from db.db_helper import db_helper
from db.models import FarmaUser
from loader import bot


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FIRST_MESSAGE = """
<b>Как не остаться один на один со сложным кейсом в терапии?</b>

В частной практике коммуникация с психиатрами — это квест:
▶️ сложно выйти на контакт
▶️ врачебная тайна
▶️ разногласия в целях и методах терапии и много чего еще.

Где заканчивается ваша ответственность и начинается работа врача? Как не брать на себя лишнее и не упустить опасные симптомы?

Мы подготовили серию видео, чтобы вы чувствовали себя чуточку увереннее:

🔹 Как психологу и психиатру работать вместе, чтобы усилить результат терапии?
🔹 Где проходит граница между психологическим запросом и состоянием, требующим медицинской поддержки?
🔹 Как выглядит работа психиатра?

Смотреть на <a href="https://www.youtube.com/watch?v=dpOkOg8vGsQ&list=PLag8fbe4g3mGEtsPuSDnwCorpWtMuPoZX">YouTube</a> и в <a href="https://vkvideo.ru/@p_c_school/playlists">ВК Видео</a>
"""

SECOND_MESSAGE = """
<b>Фармакотерапия для психологов: как понимать назначения психиатра и работать безопасно</b>

Напоминаем, что уже через 2 дня состоится вебинар "Фармакотерапия для психологов".

Мы намеренно сделали короткий формат, чтобы как можно больше психологов смогли вписать вебинар в свой учебный график. По шагу за раз к знаниям, которые всегда "не срочные" 😚

<b>Содержание вебинара:</b>
• Какие препараты используются в психиатрии
• Антипсихотики
• Антидепрессанты
• Влияние антидепрессантов на психотерапию
• Основные принципы и длительность лечения
• Когда нужна консультация психиатра
• Бывают ли неэффективные препараты

<b>Вот какими частыми проблемами делятся психологи:</b>
• <i>"У меня нет актуальной информации о лекарствах (новых, проверенных, устаревших и т.д.) и я с трудом ориентируюсь в том, что рекомендуют врачи"</i>

• <i>"Нужно понимание как фарма повлияет на терапевтический процесс. Какие изменения в лечении к чему ведут."</i>

• <i>"Мне попадались клиенты и клиентки со сложными коморбидностями и не очень подходящим назначенным лечением. Им не помогало то, что они принимали (или даже вредило), а моих знаний не было достаточно, чтобы разобраться"</i>

Все эти проблемы и даже больше в рамках вебинара мы обсудим.

📘 <b>Ведущий</b>
Максим Резников  
Психиатр, КПТ и схема-терапевт. Опыт работы — более 10 лет.

Встреча через 2 дня!  
<a href="https://clck.ru/3S4kNR">Подробнее о программе вебинара</a>
"""

async def get_users():
    async with db_helper.session_factory() as session:
        result = await session.execute(select(FarmaUser.tg_id))
        return [row[0] for row in result.all()]

async def broadcast(users, text):
    sent = 0

    for user_id in users:
        try:
            await bot.send_message(user_id, text, disable_web_page_preview=True, parse_mode="HTML",)
            sent += 1

            await asyncio.sleep(0.05)

        except Exception as e:
            logger.warning(f"Failed to send to {user_id}: {e}")

    logger.info(f"Sent {sent}/{len(users)} messages")


async def main():


    users = [846222946]
    logger.info(f"Loaded {len(users)} users")

    logger.info("Sending first message")
    await broadcast(users, FIRST_MESSAGE)
    logger.info("Waiting 5 seconds...")
    await asyncio.sleep(5)
    logger.info("Sending second message")
    await broadcast(users, SECOND_MESSAGE)


    await asyncio.sleep(600)

    users1 = await get_users()

    logger.info(f"Loaded {len(users1)} users")

    logger.info("Sending first message")
    await broadcast(users1, FIRST_MESSAGE)
    logger.info("Waiting 5 minutes...")
    await asyncio.sleep(300)
    logger.info("Sending second message")
    await broadcast(users1, SECOND_MESSAGE)


if __name__ == "__main__":
    asyncio.run(main())