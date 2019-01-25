# -*- coding: utf-8 -*-
'''
Proxy minion interface module for interacting with Heroku apps.
'''

# Import Python Libs
from __future__ import absolute_import
import logging

# import Salt Libs
from salt.utils.dictupdate import merge

DETAILS = {}

log = logging.getLogger(__name__)

__proxyenabled__ = ['heroku']
__virtualname__ = 'heroku'


def __virtual__():
    '''
    Only return if all the modules are available
    '''
    log.info('heroku proxy __virtual__() called...')
    return __virtualname__


def init(opts):
    log.debug('heroku proxy init() called...')
    log.debug('Validating heroku proxy input')
    proxy_conf = merge(opts.get('proxy', {}), __pillar__.get('proxy', {}))
    log.trace('proxy_conf = %s', proxy_conf)

    DETAILS['proxytype'] = proxy_conf['proxytype']
    DETAILS['initialized'] = True
    return True


def initialized():
    '''
    Return whether init() function has been called
    '''
    return DETAILS.get('initialized', False)


def get_details():
    '''
    Return the proxy details
    '''
    return DETAILS


def shutdown():
    '''
    Shutdown the connection to the proxy device. For this proxy,
    shutdown is a no-op.
    '''
    log.debug('Heroku proxy shutdown() called...')
