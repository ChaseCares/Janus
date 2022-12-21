import logging
import os

def setupLogger(loggerName, logFile, level=logging.DEBUG):
    if not os.path.isdir('./log'):
        os.mkdir('./log')

    log = logging.getLogger(loggerName)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s: %(message)s',
        datefmt = '%m/%d/%Y %I:%M:%S %p')
    fileHandler = logging.FileHandler(logFile, mode='a', encoding='utf-8')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    log.setLevel(level)
    log.addHandler(fileHandler)
    log.addHandler(streamHandler)
    return logging.getLogger(loggerName)
