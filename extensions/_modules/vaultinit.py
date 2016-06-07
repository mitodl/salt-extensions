# -*- coding: utf-8 -*-
"""
This module will initialize an installation of Hashicorp Vault in an idempotent
manner.
"""
from __future__ import absolute_import

import logging
import inspect

log = logging.getLogger(__name__)

try:
    import hvac
    import requests
    DEPS_INSTALLED = True
except ImportError:
    log.debug('Unable to import the HVAC library.')
    DEPS_INSTALLED = False


class InsufficientParameters(Exception):
    pass

def __virtual__():
    return DEPS_INSTALLED


def _build_client(vault_url='https://localhost:8200', token=None, cert=None,
                  verify=True, timeout=30, proxies=None, allow_redirects=True,
                  session=None):
    client_kwargs = locals()
    for k, v in client_kwargs.items():
        client_kwargs[k] = __salt__['config.get'](
            'vault:{key}'.format(key=k), v)
    return hvac.Client(**client_kwargs)


def _get_keybase_pubkey(username):
    user = requests.get('https://keybase.io/{username}/key.asc'.format(
        username=username))
    user.raise_for_status()
    return user.text


def _unseal(sealing_keys):
    client = _build_client()
    client.unseal_multi(sealing_keys)


def _rekey(secret_shares, secret_threshold, sealing_keys, pgp_keys):
    client = _build_client()
    rekey = client.start_rekey(secret_shares, secret_threshold, pgp_keys,
                               backup=True)
    client.rekey_multi(sealing_keys, nonce=rekey['nonce'])


def initialize(secret_shares=5, secret_threshold=3, pgp_keys=None,
               keybase_users=None, unseal=True):
    success = True
    if keybase_users and isinstance(keybase_users, list):
        keybase_keys = []
        for user in keybase_users:
            keybase_keys.append(_get_keybase_pubkey(user))
        (pgp_keys or []).extend(keybase_keys)
    if pgp_keys and len(pgp_keys) < secret_shares:
        raise InsufficientParameters('The number of PGP keys does not match'
                                     ' the number of secret shares.')
    client = _build_client()
    try:
        sealing_keys = client.initialize(secret_shares, secret_threshold).json()
        if unseal:
            _unseal(sealing_keys['keys'])
        if pgp_keys:
            _rekey(secret_shares, secret_threshold, sealing_keys['keys'], pgp_keys)
            sealing_keys = client.get_backed_up_keys()['keys']
    except hvac.exceptions.VaultError:
        success = False
        sealing_keys = None
    return success, sealing_keys


def is_initialized():
    client = _build_client()
    return client.is_initialized()
