import logging
from datetime import datetime
import atexit
import time

# 1. Configure the log file and the minimum logging level
logging.basicConfig(
    filename='results_gradient_search.log',
    filemode='w',
    encoding='utf-8',
    level=logging.INFO,
    format="%(message)s",
)

timestamp_start = datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
logging.info(f'Program started at {timestamp_start}')

start_time = time.perf_counter()

def log_duration():
    duration = time.perf_counter() - start_time
    logging.info(f"\n[Runtime] {duration:.4f} Sekunden")
    timestamp_end = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logging.info(f"Programm finished at {str(timestamp_end)}")

atexit.register(log_duration)