# coding: utf-8
"""
logging.py -- creates ecell-domain root logger.

Ported from epdp/gfrdbase.py
"""

import logging, logging.handlers, os


def setup(logger_name='ecell', fallback_handler=None, fallback_level=None,
                 format='%(message)s'):
    """Setup root logger.

    logger_name: name of the logger.
    fallback_handler: logging handler to fallback if LOGFILE isn't set.
    fallback_level: logging level to fallback if LOGLEVEL isn't set.
    format: log format.

    # setup
    >>> import os, tempfile
    >>> tfname = tempfile.mktemp()

    # default setup() yields logger 'ecell' with StreamHandler(INFO).
    >>> logger = setup()
    >>> logger
    <logging.Logger object at ...>
    >>> logger.name, logger.level==logging.INFO
    ('ecell', True)
    >>> logger.handlers
    [..., <logging.StreamHandler ...>]

    # setting fallback_handler causes fallback.
    >>> class DummyHandler(object):
    ...   def setFormatter(self, fmt): pass
    ...   def setLevel(self, lvl): pass
    ...   def __repr__(self): return '<DummyHandler>'
    ...
    >>> logger = setup(fallback_handler=DummyHandler(),
    ...                fallback_level=logging.DEBUG)
    >>> logger.handlers, logger.level==logging.DEBUG
    ([..., <DummyHandler>], True)

    # setting LOGFILE make use of FileHandler.
    >>> os.environ['LOGFILE'] = tfname
    >>> logger = setup()
    >>> logger.handlers
    [..., <logging.FileHandler ...>]

    # setting valid LOGSIZE make use of RotatingHandler.
    >>> os.environ['LOGSIZE'] = '2000'
    >>> logger = setup()
    >>> logger.handlers
    [..., <logging.handlers.RotatingFileHandler ...>]

    # teardown
    >>> if os.path.exists(tfname): os.remove(tfname)
    
    """
    log_file = os.environ.get('LOGFILE', None)
    log_level = os.environ.get('LOGLEVEL', None)
    log_size = int(os.environ.get('LOGSIZE', '0'))
    logger = logging.getLogger(logger_name)
    handler, default_level = None, None
    if log_file:
        # raise ValueError(int(log_size))
        if log_size:
            handler = logging.handlers.RotatingFileHandler(
                log_file, mode='w', maxBytes=int(log_size))
        else:
            handler = logging.FileHandler(log_file, 'w')
        default_level = logging.INFO
    elif fallback_handler and fallback_level:
        handler, default_level = fallback_handler, fallback_level
    else:
        handler, default_level = logging.StreamHandler(), logging.INFO
    handler.setLevel(log_level or default_level)
    logger.setLevel(log_level or default_level)
    handler.setFormatter(logging.Formatter(format))
    logger.addHandler(handler)
    return logger


# creates logger
logger = setup()


if __name__=='__main__':
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
