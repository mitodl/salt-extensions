from __future__ import absolute_import

import logging

log = logging.getLogger(__name__)

try:
    import hvac
    DEPS_INSTALLED = True
except ImportError:
    log.debug('Unable to import the HVAC library.')
    DEPS_INSTALLED = False


def __virtual__():
    return DEPS_INSTALLED


def initialize(name, secret_shares=5, secret_threshold=3, pgp_keys=None,
               keybase_users=None, unseal=True):
    ret = {'name': name,
           'comment': '',
           'result': '',
           'changes': {}}
    initialized = __salt__['vaultinit.is_initialized']()
    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Vault will {}be initialized.'.format(
            'not ' if initialized else '')
    else:
        success, sealing_keys = __salt__['vaultinit.initalize'](
            secret_shares, secret_threshold, pgp_keys, keybase_users, unseal
        ) if not initialized else (True, [])
        ret['result'] = success
        ret['changes'] = {
            'new': sealing_keys,
            'old': []
        }
        ret['comment'] = 'Vault is {}initialized'.format(
            '' if success else 'not ')
    return ret
