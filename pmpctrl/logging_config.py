import logging

from time import gmtime

logging.Formatter.converter = gmtime

logging.basicConfig(
    format = '%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(name)-16s | %(funcName)-16s | %(message)s',
    datefmt = '%Y-%m-%dT%H:%M:%S'
)