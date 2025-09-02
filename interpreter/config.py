import logging
import os


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_IMAGE_DIR = "/tmp"
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)


