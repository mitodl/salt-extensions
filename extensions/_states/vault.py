from __future__ import absolute_import

import logging

log = logging.getLogger(__name__)

try:
    import hvac
    DEPS_INSTALLED = True
except ImportError:
    log.debug('Unable to import the HVAC library.')
    DEPS_INSTALLED = False

__all__ = ['initialize']


def __virtual__():
    return DEPS_INSTALLED


def initialized(name, secret_shares=5, secret_threshold=3, pgp_keys=None,
               keybase_users=None, unseal=True):
    ret = {'name': name,
           'comment': '',
           'result': '',
           'changes': {}}
    initialized = __salt__['vault.is_initialized']()

    if initialized:
        ret['result'] = True
        ret['Comment'] = 'Vault is already initialized'
    elif __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Vault will be initialized.'
    else:
        success, sealing_keys, root_token = __salt__['vault.initialize'](
            secret_shares, secret_threshold, pgp_keys, keybase_users, unseal
        ) if not initialized else (True, {}, '')
        ret['result'] = success
        ret['changes'] = {
            'root_credentials': {
                'new': {
                    'sealing_keys': sealing_keys,
                    'root_token': root_token
                },
                'old': {}
            }
        }
        ret['comment'] = 'Vault has {}initialized'.format(
            '' if success else 'not ')
    return ret


def auth_backend_enabled(backend_type, description='', mount_point=None):
    backends = __salt__['vault.list_auth_backends']()
    setting_dict = {'type': backend_type, 'description': description}
    backend_enabled = False
    ret = {'name': name,
           'comment': '',
           'result': '',
           'changes': {'auth_backends': {'old': backends}}}

    for path, settings in __salt__['vault.list_auth_backends']().items():
        if (path.strip('/') == mount_point or backend_type and
            settings['type'] == backend_type):
            backend_enabled = True

    if backend_enabled:
        ret['comment'] = ('The {auth_type} backend mounted at {mount} is already'
                          ' enabled.'.format(auth_type=backend_type,
                                             mount=mount_point))
        ret['result'] = True
    elif __opts__['test']:
        ret['result'] = None
    else:
        try:
            __salt__['vault.enable_auth_backend'](backend_type,
                                                  description=description,
                                                  mount_point=mount_point)
            ret['result'] = True
            ret['changes']['backends']['new'] = __salt__[
                'vault.list_auth_backends']()
        except hvac.exceptions.VaultError as e:
            ret['result'] = False
            log.exception(e)
        ret['comment'] = ('The {backend} has been successfully mounted at '
                          '{mount}.'.format(backend=backend_type,
                                            mount=mount_point))
    return ret


def audit_backend_enabled(backend_type, description='', options=None,
                          mount_point=None):
    backends = __salt__['vault.list_audit_backends']()
    setting_dict = {'type': backend_type, 'description': description}
    backend_enabled = False
    ret = {'name': name,
           'comment': '',
           'result': '',
           'changes': {'audit_backends': {'old': backends}}}

    for path, settings in __salt__['vault.list_audit_backends']().items():
        if (path.strip('/') == mount_point or backend_type and
            settings['type'] == backend_type):
            backend_enabled = True

    if backend_enabled:
        ret['comment'] = ('The {audit_type} backend mounted at {mount} is already'
                          ' enabled.'.format(audit_type=backend_type,
                                             mount=mount_point))
        ret['result'] = True
    elif __opts__['test']:
        ret['result'] = None
    else:
        try:
            __salt__['vault.enable_audit_backend'](backend_type,
                                                  description=description,
                                                  mount_point=mount_point)
            ret['result'] = True
            ret['changes']['backends']['new'] = __salt__[
                'vault.list_audit_backends']()
        except hvac.exceptions.VaultError as e:
            ret['result'] = False
            log.exception(e)
        ret['comment'] = ('The {backend} has been successfully mounted at '
                          '{mount}.'.format(backend=backend_type,
                                            mount=mount_point))
    return ret


def app_id_created(app_id, policies, display_name=None, mount_point='app-id',
                   **kwargs):
    pass


def policy_created(name, rules):
    current_policy = __salt__['vault.get_policy'](name, parse=True)
    ret = {'name': name,
           'comment': '',
           'result': False,
           'changes': {}}
    if current_policy == rules:
        ret['result'] = True
        ret['comment'] = ('The {policy_name} policy already exists with the '
                          'given rules.'.format(policy_name=name))
    elif __opts__['test']:
        ret['result'] = None
        if current_policy:
            ret['changes']['old'] = current_policy
            ret['changes']['new'] = rules
        ret['comment'] = ('The {policy_name} policy will be {suffix}.'.format(
            policy_name=name,
            suffix='updated' if current_policy else 'created'))
    else:
        try:
            __salt__['vault.set_policy'](name, rules)
            ret['result'] = True
            ret['comment'] = ('The {policy_name} policy was successfully '
                              'created/updated.'.format(policy_name=name))
            ret['changes']['old'] = current_policy
            ret['changes']['new'] = rules
        except hvac.exceptions.VaultError as e:
            log.exception(e)
            ret['comment'] = ('The {policy_name} policy failed to be '
                              'created/updated'.format(policy_name=name))
    return ret
