# -*- coding: utf-8 -*-
'''
State for managing heroku apps.

:configuration: This state can be used by either passing an api key directly
    or by specifying it in a configuration profile in pillar.

    It is possible to use a different API than http://api.heroku.com,
    by specifying the API URL in config as api_url, or by passing the value directly.

    For example:

    .. code-block:: yaml

        heroku.<name_of_state>:
          - api_key: your_api_key
'''
from __future__ import absolute_import
import logging
import salt.config
import sys

log = logging.getLogger(__name__)

# Global keys to maintain state of dict mismatch between Heroku and Pillar
diff_heroku_pillar_dict = {'key_or_value_mismatch': False,
                           'heroku_not_pillar': False,
                           'pillar_not_heroku': False}

# Global dicts to store diffs between Heroku and Pillar config vars
heroku_diff_dict = {}
pillar_diff_dict = {}


def __virtual__():
    '''
    Return virtual name of the module.

    :return: The virtual name of the module.
    '''
    return True


def _diff_app_config_vars(name, config_vars, api_key):
    '''
    Compare keys and values between Heroku and Pillar config vars.
    This function makes no changes to Heroku config vars and only
    lists differences.

    :param name: The name of the Heroku app
    :param config_vars: The config_vars specified in pillar
    :param api_key: The Heroku api_key
    :returns: Result of executing the state
    :rtype: dict
    '''

    ret = {'name': name,
           'comment': '',
           'result': None,
           'changes': {}}

    try:
        app_config_vars = __salt__['heroku.list_app_config_vars'](name, api_key)
        log.debug("Calling _diff_heroku_pillar_vars")
        _diff_heroku_pillar_vars(app_config_vars, config_vars)
        if all(not v for v in diff_heroku_pillar_dict.values()):
            ret['result'] = True
            ret['comment'] = 'No changes detected'
        else:
            ret['result'] = False
            ret['comment'] = 'Pillar and Heroku mismatch'
            ret['changes'] = {'old': {'heroku': heroku_diff_dict, 'pillar': pillar_diff_dict}}
    except:
        e = sys.exc_info()[0]
        ret['result'] = False
        log.exception(e)

    return ret


def _diff_heroku_pillar_vars(app_config_vars, config_vars):
    '''
    Internal function that runs multiple set operations on Heroku and Pillar
    dicts and sets the values on diff_heroku_pillar_dict accordingly

    :param app_config_vars: The Heroku configuration variables
    :param config_vars: The Pillar configuration variables
    :returns: three global dicts
    '''

    global diff_heroku_pillar_dict, heroku_diff_dict, pillar_diff_dict
    app_config_vars_set = set(app_config_vars.items())
    config_vars_set = set(config_vars.items())

    if app_config_vars_set.symmetric_difference(config_vars_set):
        diff_heroku_pillar_dict['key_or_value_mismatch'] = True
        heroku_diff_dict = dict(app_config_vars_set.difference(config_vars_set))
        pillar_diff_dict = dict(config_vars_set.difference(app_config_vars_set))
    if len(app_config_vars) - len(config_vars) > 0:
        diff_heroku_pillar_dict['heroku_not_pillar'] = True
    if len(app_config_vars) - len(config_vars) < 0:
        diff_heroku_pillar_dict['pillar_not_heroku'] = True

    log.debug("Completed _diff_heroku_pillar_vars")
    return diff_heroku_pillar_dict, heroku_diff_dict, pillar_diff_dict


def update_app_config_vars(name, config_vars, api_key):
    '''
    Update Heroku config vars based on specified pillar config vars.
    This function will perform the following actions:
      - Change Heroku config var values for the keys that match one in pillar
      - Add keys from pillar to Heroku
      - Leave Heroku keys not find in pillar unchanged

    :param name: The name of the Heroku app
    :param config_vars: The config_vars specified in pillar
    :param api_key: The Heroku api_key
    :returns: Result of executing the state
    :rtype: dict
    '''

    ret = {'name': name,
           'comment': '',
           'result': True,
           'changes': {}}

    diff_app_config_vars = _diff_app_config_vars(name, config_vars, api_key)
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Following changes would be performed'
        ret['changes'] = diff_app_config_vars
        return ret
    if any(v for v in diff_heroku_pillar_dict.values()):
        __salt__['heroku.update_app_config_vars'](name, config_vars, api_key)
        new_app_config_vars = __salt__['heroku.list_app_config_vars'](name, api_key)
        ret['changes']['new'] = {'heroku': new_app_config_vars}
    return ret


def override_app_config_vars(name, config_vars, api_key):
    '''
    * WARNING * Destructive Function
    This function will delete all Heroku config var keys and values and
    replace them with ones specified in pillar

    :param name: The name of the Heroku app
    :param config_vars: The config_vars specified in pillar
    :param api_key: The Heroku api_key
    :returns: Result of executing the state
    :rtype: dict
    '''

    ret = {'name': name,
           'comment': 'Heroku config variables have been overwritten',
           'result': True,
           'changes': {}}

    try:
        app_config_vars = __salt__['heroku.list_app_config_vars'](name, api_key)
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'Following changes would be performed'
            ret['changes'] = config_vars
            return ret
        empty_values = dict.fromkeys(app_config_vars)
        for key, value in empty_values.items():
            if value is None:
                values = ''
                empty_values[key] = value

        log.debug("Created empty_dict")
        __salt__['heroku.update_app_config_vars'](name, empty_values, api_key)
        __salt__['heroku.update_app_config_vars'](name, config_vars, api_key)
        ret['changes']['old'] = {'heroku': app_config_vars}
        ret['changes']['new'] = {'heroku': config_vars}
    except:
        e = sys.exc_info()[0]
        ret['result'] = False
        log.exception(e)

    return ret
