import logging
import os

class Logger:

    def __init__(self, log_dir):
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            filename=os.path.join(log_dir, "app.log"),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def info(self, msg):
        logging.info(msg)

    def error(self, msg):
        logging.error(msg)