# -*- coding: utf-8 -*-
'''
Module for managing heroku apps.

.. versionadded:: 2015.5.0

:configuration: This module can be used by either passing an api key and version
    directly or by specifying both in a configuration profile in the salt
    master/minion config.

    For example:

    .. code-block:: yaml

        heroku:
          api_key: peWcBiMOS9HrZG15peWcBiMOS9HrZG15

    Custom API Example:

    .. code-block:: yaml

        heroku:
          api_url: http://api.heroku.myteam.com
          api_key: peWcBiMOS9HrZG15peWcBiMOS9HrZG15
'''
# Import Python Libs
from __future__ import absolute_import
import json
import logging

# Import 3rd-party Libs
# pylint: disable=import-error,no-name-in-module,redefined-builtin
from salt.ext.six.moves.urllib.parse import urljoin as _urljoin
from salt.ext.six.moves.urllib.parse import urlencode as _urlencode
from salt.ext.six.moves import range
import salt.ext.six.moves.http_client

import salt.utils.http

# pylint: enable=import-error,no-name-in-module,redefined-builtin

log = logging.getLogger(__name__)

__virtualname__ = 'heroku'

def __virtual__():
    '''
    Return virtual name of the module.

    :return: The virtual name of the module.
    '''
    return __virtualname__

def _query(
       api_url=None,
       api_key=None,
       endpoint=None,
       arguments=None,
       method='GET',
       data=None):
  '''
  Heroku object method function to construct and execute on the API URL.

  :param api_url:     The Heroku API URL.
  :param api_key:     The Heroku api key.
  :param function:    The Heroku api function to perform.
  :param method:      The HTTP method, e.g. GET, POST, or PATCH.
  :param data:        The data to be sent for POST/PATCH method.
  :return:            The json response from the API call or False.
  '''
  headers = {}
  query_params = {}

  if not api_url:
      try:
          options = __salt__['config.option']('heroku')
          api_url = options.get('api_url')
      except (NameError, KeyError, AttributeError):
          pass  # not mandatory, thus won't fail if not found

  if not api_key or not endpoint:
      try:
          options = __salt__['config.option']('heroku')
          if not api_key:
            api_key = options.get('api_key')
          if not endpoint:
            endpoint = options.get('endpoint')
      except (NameError, KeyError, AttributeError):
          log.error("No Heroku api key or endpoint found.")
          return False

  use_api_url = 'https://api.heroku.com'  # default API URL
  if api_url:
      use_api_url = api_url
  url = _urljoin(use_api_url, endpoint + '/')
  if arguments:
    url = _urljoin(url, arguments + '/')

  if endpoint:
    headers['Authorization'] = 'Bearer {0}'.format(api_key)
    headers['Accept'] = 'application/vnd.heroku+json; version=3'
    if data:
      data = json.dumps(data)

    if method == 'POST' or method == 'PATCH':
      headers['Content-Type'] = 'application/json'
  else:
    log.error('Heroku endpoint not specified')
    return False

  result = salt.utils.http.query(
      url,
      method,
      params=query_params,
      data=data,
      decode=True,
      status=True,
      header_dict=headers,
      opts=__opts__,
  )

  if result.get('status', None) == salt.ext.six.moves.http_client.OK:
      return result.get('dict', {})
  elif result.get('status', None) == salt.ext.six.moves.http_client.NO_CONTENT:
      return False
  else:
      log.debug(url)
      log.debug(query_params)
      log.debug(data)
      log.debug(result)
      if result.get('error'):
          log.error(result)
      return False

def list_apps(api_url=None,
               api_key=None,
               endpoint=None):
    '''
    List all Heroku apps.

    :param api_url: The Heroku API URL, if not specified in the configuration.
    :param api_key: The Heroku admin api key.
    :return: The apps list.

    CLI Example:

    .. code-block:: bash

        salt '*' heroku.list_rooms

        salt '*' heroku.list_rooms api_key=peWcBiMOS9HrZG15peWcBiMOS9HrZG15
    '''
    foo = _query(endpoint='apps',
                 api_url=api_url,
                 api_key=api_key)
    log.debug('foo {0}'.format(foo))
    return foo

def app_info(app_name,
             api_url=None,
             api_key=None,
             endpoint=None):

    foo = _query(endpoint='apps',
               arguments=app_name,
               api_url=api_url,
               api_key=api_key)
    log.debug('foo {0}'.format(foo))
    return foo

def list_buildpacks(app_name,
             api_url=None,
             api_key=None,
             endpoint=None):

    foo = _query(endpoint='apps',
               arguments=app_name+'/buildpack-installations',
               api_url=api_url,
               api_key=api_key)
    log.debug('foo {0}'.format(foo))
    return foo

def list_config_vars(app_name,
             api_url=None,
             api_key=None,
             endpoint=None):

    foo = _query(endpoint='apps',
               arguments=app_name+'/config-vars',
               api_url=api_url,
               api_key=api_key)
    log.debug('foo {0}'.format(foo))
    return foo

def set_config_vars(app_name,
             parameters,
             api_url=None,
             api_key=None,
             endpoint=None):

    parameters = dict()
    parameters['data'] = data

    result = _query(endpoint='apps',
               arguments=app_name+'/config-vars',
               api_url=api_url,
               api_key=api_key,
               method='PATCH',
               data=parameters)
    if result:
      return True
    else:
      return False

