# -*- coding: utf-8 -*-
'''
Beacon to manage and report the status of a server status endpoint.
Fire an event when specified values don't match returned response.

'''

# Import Python libs
from __future__ import absolute_import, unicode_literals
import logging
import operator
import re
import requests
import salt.utils
from salt.ext.six.moves import map

log = logging.getLogger(__name__)

__virtualname__ = 'http_status'

comparisons = {
  '=': operator.eq,
  '<': operator.lt,
  '>': operator.gt,
  '<=': operator.le,
  '>=': operator.ge,
  '!=': operator.ne,
  'search': re.search
}


def __virtual__():
    return __virtualname__


def validate(config):
    '''
    Validate the beacon configuration
    '''
    if not isinstance(config, list):
        return False, ('Configuration for %s beacon must '
                       'be a list.', __virtualname__)
    else:
        _config = {}
        list(map(_config.update, config))

        if 'sites' not in _config:
            return False, ('Configuration for %s beacon '
                           'requires sites.', __virtualname__)
        else:
            if not isinstance(_config['sites'], list):
                return False, ('Sites for %s beacon '
                               'must be a list.', __virtualname__)
            else:
                for sites in _config['sites']:
                    log.debug('_config %s', _config['sites'][sites])
                    if 'status_endpoint' not in _config['sites'][sites]:
                        return False, ('Sites for %s beacon '
                                       'requires status_endpoint.', __virtualname__)
                    if 'json_response' not in _config['sites'][sites]:
                        return False, ('Sites for %s beacon '
                                       'requires json_response.', __virtualname__)
                    else:
                        _json_response = _config['sites'][sites]['json_response']
                        if not isinstance(_json_response, dict):
                            return False, ('json_response for %s beacon '
                                           'must be a dict.', __virtualname__)
    return True, 'Valid beacon configuration'


def beacon(config):
    '''
    Check on different service status reported by the django-server-status
    library.

    .. code-block:: yaml

        beacons:
          http_status:
            - sites:
                example-site-1:
                  status_endpoint: "https://example.com/status"
                  json_response:
                    - path: 'redis:status'
                      value: 'up'
                      comp: '='
                    - path: 'postgresql:response_microseconds'
                      value: 50
                      comp: '<='
                  html_response:
                    - path: ''
                      value: 'foo.*bar'
                      comp: search
    '''
    ret = []

    _config = {}
    list(map(_config.update, config))

    for sites in _config.get('sites', ()):
        sites_config = _config['sites'][sites]
        status_endpoint = sites_config['status_endpoint']
        try:
            if 'timeout' in sites_config:
                r = requests.get(status_endpoint, timeout=sites_config['timeout'])
            else:
                r = requests.get(status_endpoint, timeout=30)
        except requests.exceptions.RequestException as e:
            log.debug("Request failed: ", e)
        for json_response_item in sites_config['json_response']:
            service = json_response_item['path'].split(':')[0]
            service_value = json_response_item['path'].split(':')[1]
            if service in r.json():
                if json_response_item['comp'] in comparisons:
                    comp = comparisons[json_response_item['comp']]
                    if not comp(json_response_item['value'],
                                r.json()[service][service_value]):
                        _failed = {'service': service,
                                   'status': json_response_item['value'],
                                   'comp': comp,
                                   }
                        ret.append(_failed)
                else:
                    log.debug('Comparison operator not in comparisons dict: '
                              ' %s', json_response_item['value'])
            else:
                log.debug('Server status response does not include listed '
                          'service in path: %s', service)
        for html_response_item in sites_config['html_response']:
            search_value = html_response_item['value']
            comp = comparisons[html_response_item['comp']]
            if not comp(search_value, r.text):
                ret.append({'keyword': search_value})
    return ret
