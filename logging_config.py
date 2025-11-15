# logging_config.py
import logging

# Set up logging configuration
logging.basicConfig(level=logging.WARNING)

# Adjust SQLAlchemy logging level
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)