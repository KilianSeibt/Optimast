import logging

# 1. Configure the log file and the minimum logging level
logging.basicConfig(
    filename='results_gradient_search.log',
    filemode='w',
    encoding='utf-8',
    level=logging.INFO
)