import logging
import os


def setup_logger():
    logger = logging.getLogger("MedicalChatBot")
    logger.setLevel(logging.INFO)

    # Create file handler
    if not os.path.exists("logs"):
        os.makedirs("logs")

    fh = logging.FileHandler("logs/chatbot.log", encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


logger = setup_logger()