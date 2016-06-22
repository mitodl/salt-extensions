# -*- coding: utf-8 -*-
"""
This module provides methods for interacting with Hashicorp Vault via the HVAC
library.
"""
from __future__ import absolute_import

import logging
import inspect
from functools import wraps

log = logging.getLogger(__name__)
EXCLUDED_HVAC_FUNCTIONS = ['initialize']

try:
    import hvac
    import requests
    DEPS_INSTALLED = True
except ImportError:
    log.debug('Unable to import the HVAC library.')
    DEPS_INSTALLED = False

__all__ = ['initialize', 'is_initialized']

class InsufficientParameters(Exception):
    pass

def __virtual__():
    return DEPS_INSTALLED


def _build_client(url='https://localhost:8200', token=None, cert=None,
                  verify=True, timeout=30, proxies=None, allow_redirects=True,
                  session=None):
    client_kwargs = locals()
    for k, v in client_kwargs.items():
        arg_val = __salt__['config.get']('vault.{key}'.format(key=k), v)
        log.debug('Setting {0} parameter for HVAC client to {1}.'
                  .format(k, arg_val))
        client_kwargs[k] = arg_val
    return hvac.Client(**client_kwargs)


def _bind_client(unbound_function):
    @wraps(unbound_function)
    def bound_function(*args, **kwargs):
        client = _build_client()
        return unbound_function(client, *args, **kwargs)
    return bound_function


def _get_keybase_pubkey(username):
    """
    Return the base64 encoded public PGP key for a keybase user.
    """
    # Retrieve the text of the public key stored in Keybase
    user = requests.get('https://keybase.io/{username}/key.asc'.format(
        username=username))
    # Explicitly raise an exception if there is an HTTP error. No-op if no error
    user.raise_for_status()
    # Process the key to only include the contents and not the wrapping
    # contents (e.g. ----BEGIN PGP KEY---)
    user_key = user.text
    key_lines = user.text.strip('\n').split('\n')
    key_lines = key_lines[key_lines.index(''):-2]
    return ''.join(key_lines)


def _unseal(sealing_keys):
    client = _build_client()
    client.unseal_multi(sealing_keys)


def _rekey(secret_shares, secret_threshold, sealing_keys, pgp_keys, root_token):
    client = _build_client(token=root_token)
    rekey = client.start_rekey(secret_shares, secret_threshold, pgp_keys,
                               backup=True)
    client.rekey_multi(sealing_keys, nonce=rekey['nonce'])


def initialize(secret_shares=5, secret_threshold=3, pgp_keys=None,
               keybase_users=None, unseal=True):
    success = True
    if keybase_users and isinstance(keybase_users, list):
        keybase_keys = []
        for user in keybase_users:
            log.debug('Retrieving public keys for Keybase user {}.'
                      .format(user))
            keybase_keys.append(_get_keybase_pubkey(user))
        pgp_keys = pgp_keys or []
        pgp_keys.extend(keybase_keys)
    if pgp_keys and len(pgp_keys) < secret_shares:
        raise InsufficientParameters('The number of PGP keys does not match'
                                     ' the number of secret shares.')
    client = _build_client()
    try:
        if pgp_keys and not unseal:
            secrets = client.initialize(secret_shares, secret_threshold,
                                        pgp_keys)
        else:
            secrets = client.initialize(secret_shares, secret_threshold)
        sealing_keys = secrets['keys']
        root_token = secrets['root_token']
        if unseal:
            log.debug('Unsealing Vault with generated sealing keys.')
            _unseal(sealing_keys)
    except hvac.exceptions.VaultError as e:
        log.exception(e)
        success = False
        sealing_keys = None
    try:
        if pgp_keys and unseal:
            log.debug('Regenerating PGP encrypted keys and backing them up.')
            log.debug('PGP keys: {}'.format(pgp_keys))
            _rekey(secret_shares, secret_threshold, sealing_keys,
                   pgp_keys, root_token)
            client = _build_client(token=root_token)
            encrypted_sealing_keys = client.get_backed_up_keys()['keys']
            if encrypted_sealing_keys:
                sealing_keys = encrypted_sealing_keys
    except hvac.exceptions.VaultError as e:
        ret['message'] = ('Vault was initialized but PGP keys were not able to'
                          ' be generated after unsealing.')
        log.debug('Failed to rekey and backup the sealing keys.')
        log.exception(e)
    return success, sealing_keys, root_token


def _register_functions():
    method_dict = {}
    for method_name in dir(hvac.Client):
        if not method_name.startswith('_'):
            method = getattr(hvac.Client, method_name)
            if (not isinstance(method, property) and
                  method_name not in EXCLUDED_HVAC_FUNCTIONS):
                if method_name == 'list':
                    method_name = 'list_values'
                globals()[method_name] = _bind_client(method)

if DEPS_INSTALLED:
    _register_functions()
