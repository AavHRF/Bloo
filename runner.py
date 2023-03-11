from framework.bot import Bloo
import logging
import logging.handlers


handler = logging.handlers.RotatingFileHandler(
    filename='discord.log',
    encoding='utf-8',
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)

if __name__ == "__main__":
    bot = Bloo()
    bot.run(log_handler=handler, log_level=logging.DEBUG)
