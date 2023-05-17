import logging
import os
from shared_utils.configurations import configurations


def setup_logging():
    log_level = configurations.get('logging', 'level', default='INFO')
    log_format = configurations.get('logging', 'format', default='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file_path = configurations.get('logging', 'file_path', default='logs/sprintswarm.log')

    log_dir = os.path.dirname(log_file_path)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(level=log_level, format=log_format, filename=log_file_path, filemode='a')


# Call the setup_logging function to set up the logging configuration
setup_logging()