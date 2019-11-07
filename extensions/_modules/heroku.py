# -*- coding: utf-8 -*-
'''
Module for managing heroku apps.

.. versionadded:: 2015.5.0

:configuration: This module can be used by either passing an api key directly
    or by specifying it in a configuration profile in the salt
    master/minion config.

    It is possible to use a different API than http://api.heroku.com,
    by specifying the API URL in config as api_url, or by passing the
    value directly.

    For example:

    .. code-block:: yaml

        heroku:
          api_key: peWcBiMOS9HrZG15peWcBiMOS9HrZG15
'''
# Import Python Libs
from __future__ import absolute_import
import json
import logging

# Import 3rd-party Libs
# pylint: disable=import-error,no-name-in-module,redefined-builtin
from salt.ext.six.moves.urllib.parse import urljoin as _urljoin
import salt.ext.six.moves.http_client
import salt.utils.http


log = logging.getLogger(__name__)

__virtualname__ = 'heroku'


def __virtual__():
    '''
    Return virtual name of the module.

    :return: The virtual name of the module.
    '''
    return __virtualname__


def _query(api_key=None, endpoint=None, arguments=None,
           method='GET', data=None):
    '''
    Heroku object method function to construct and execute on the API URL.

    :param api_key:     The Heroku api key.
    :param endpoint:    The Heroku api function to perform.
    :param arguments:   The Heroku arguments to pass.
    :param method:      The HTTP method, e.g. GET, POST, or PATCH.
    :param data:        The data to be sent for POST/PATCH method.
    :return:            The json response from the API call or False.
    '''
    headers = {}
    query_params = {}

    if not api_key or not endpoint:
        try:
            options = __salt__['config.option']('heroku')
            if not api_key:
                api_key = options.get('api_key')
            if not endpoint:
                endpoint = options['endpoint']
        except (NameError, KeyError, AttributeError):
            log.error("No Heroku api key or endpoint found.")
            return False

    api_url = 'https://api.heroku.com'  # default API URL
    url = _urljoin(api_url, endpoint)
    if arguments:
        url = url + '/'
        url = _urljoin(url, arguments)

    if endpoint:
        headers['Authorization'] = 'Bearer {0}'.format(api_key)
        headers['Accept'] = 'application/vnd.heroku+json; version=3'
        if data:
            data = json.dumps(data)

        if method in ['POST', 'PATCH']:
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


def list_apps(api_key=None):
    '''
    List all Heroku apps.

    :param api_key: The Heroku admin api key.
    :return: The list of apps.

    CLI Example:

    .. code-block:: bash

        salt-call heroku.list_apps

    '''

    result = _query(endpoint='apps', api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def app_info(app_name, api_key=None):
    '''
    Return all info for specificed app. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#app-info

    CLI Example:
    salt-call heroku.app_info <app_name>
    '''

    result = _query(endpoint='apps', arguments=app_name, api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def list_app_addons(app_name, api_key=None):
    '''
    List app addons. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#add-on-list-by-app

    CLI Examples:
    salt-call heroku.list_app_addons <app_name>
    '''

    result = _query(endpoint='apps',
                    arguments=app_name+'/addons',
                    api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def list_app_attachments(app_name, api_key=None):
    '''
    List app add-on attachments. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#add-on-attachment-list

    CLI Examples:
    salt-call heroku.list_app_attachments <app_name>
    '''

    result = _query(endpoint='apps',
                    arguments=app_name+'/addon-attachments',
                    api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def list_app_buildpacks(app_name, api_key=None):
    '''
    List an app's existing buildpack installations.
    This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#buildpack-installations-list

    CLI Examples:
    salt-call heroku.list_app_buildpacks <app_name>
    '''

    result = _query(endpoint='apps',
                    arguments=app_name+'/buildpack-installations',
                    api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def list_app_config_vars(app_name, api_key=None):
    '''
    List config vars for specified app. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#config-vars

    CLI Examples:
    salt-call heroku.list_app_config_vars <app_name>
    '''
    result = _query(endpoint='apps',
                    arguments=app_name+'/config-vars',
                    api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def update_app_config_vars(app_name, vars, api_key=None):
    '''
    Update or set config vars. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#config-vars-update

    CLI Examples:
    - Set/Modify config variable:
      salt-call heroku.update_config_vars <app_name> data='{"name":"value"}'

    - Delete config variable:
      salt-call heroku.update_config_vars <app_name> data='{"name":null}'
    '''
    result = _query(endpoint='apps',
                    arguments=app_name+'/config-vars',
                    api_key=api_key,
                    method='PATCH',
                    data=vars)

    return bool(result)


def list_app_dynos(app_name, api_key=None):
    '''
    List dynos for specified app. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#dyno-list

    CLI Examples:
    salt-call heroku.list_app_dynos <app_name>
    '''
    result = _query(endpoint='apps', arguments=app_name+'/dynos',
                    api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def restart_app_dynos(app_name, api_key=None):
    '''
    Restart dynos for specified app. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#dyno-restart-all

    CLI Examples:
    salt-call heroku.restart_app_dynos <app_name>
    '''
    result = _query(endpoint='apps', arguments=app_name+'/dynos',
                    method='DELETE', api_key=api_key)
    log.debug('result {0}'.format(result))
    return result


def add_app_collaborators(app_name, data, api_key=None):
    '''
    Add collaborators to a specific app. This uses the following heroku call:
    https://devcenter.heroku.com/articles/platform-api-reference#collaborator-create

    CLI Examples:
    - Add and notify collaborator:
      salt-call heroku.add_collaborators \
      data='{"user":"username@example.com","silent": false}'

    - Add and do not notify collaborator:
      salt-call heroku.add_collaborators \
      data='{"user":"username@example.com", "silent": true}'
    '''
    result = _query(endpoint='apps', arguments=app_name + '/collaborators',
                    api_key=api_key, method='POST', data=data)

    return bool(result)
