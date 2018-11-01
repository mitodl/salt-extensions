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
import salt.utils.data
from salt.ext.six.moves import map

log = logging.getLogger(__name__)

__virtualname__ = 'http_status'

comparisons = {
    '==': operator.eq,
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
    '!=': operator.ne,
    'search': re.search
}

required_site_attributes = {'url'}
optional_site_attributes = {'json_response'}


def __virtual__():
    return __virtualname__


def validate(config):
    '''
    Validate the beacon configuration
    '''
    if not isinstance(config, list):
        return False, ('Configuration for %s beacon must '
                       'be a list.', config)
    else:
        _config = {}
        list(map(_config.update, config))

    try:
        sites = _config.get('sites', {})
    except AttributeError:
        return False, ('Sites for %s beacon '
                       'must be a dict.', __virtualname__)
    if not sites:
        return False, ('You neglected to define any sites')

    for site, settings in sites.iteritems():
        if required_site_attributes.isdisjoint(set(settings.keys())):
            return False, ('Sites for {} beacon requires {}'.format(__virtualname__,
                                                                    required_site_attributes))
            if optional_site_attributes and optional_site_attributes.isdisjoint(set(settings.keys())):
                return False, ('Sites for {} beacon requires {}'.format(__virtualname__,
                                                                        optional_site_attributes))

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
                  url: "https://example.com/status"
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
        url = sites_config['url']
        try:
            r = requests.get(url, timeout=sites_config.get('timeout', 30))
        except requests.exceptions.RequestException as e:
            log.info("Request failed: %s", e)
            if r.raise_for_status:
                log.info('Response from status endpoint was invalid: '
                         '%s', r.status_code)
                _failed = {'status_code': r.status_code}
                ret.append(_failed)
                continue
        for json_response_item in sites_config.get('json_response', []):
            log.debug('[+] json_response_item: %s', json_response_item)
            if json_response_item['comp'] in comparisons:
                attr_path = json_response_item['path']
                comp = comparisons[json_response_item['comp']]
                expected_value = json_response_item['value']
                received_value = salt.utils.data.traverse_dict_and_list(r.json(), attr_path)
                if received_value is None:
                    log.info('No data found at location {} for url {}'.format(attr_path, url))
                    continue
                log.debug('[+] expected_value: %s', expected_value)
                log.debug('[+] received_value: %s', received_value)
                if not comp(expected_value, received_value):
                    _failed = {'expected': expected_value,
                               'received': received_value,
                               'url': url,
                               'path': attr_path
                               }
                    ret.append(_failed)
            else:
                log.info('Comparison operator not in comparisons dict: '
                         '%s', expected_value)
        for html_response_item in sites_config.get('html_response', []):
            search_value = html_response_item['value']
            comp = comparisons[html_response_item['comp']]
            if not comp(search_value, r.text):
                ret.append({'keyword': search_value})
    return ret
