# -*- coding: utf-8 -*-
# Keeping this in salt-extensions until https://github.com/saltstack/salt/pull/56146 is merged and released
'''
Consul sdb Module

:maintainer:    SaltStack
:maturity:      New
:platform:      all

This module allows access to Consul using an ``sdb://`` URI

Like all sdb modules, the Consul module requires a configuration profile to
be configured in either the minion or master configuration file. This profile
requires very little. For example:

.. code-block:: yaml

    myconsul:
      driver: consul
      host: 127.0.0.1
      port: 8500
      token: b6376760-a8bb-edd5-fcda-33bc13bfc556
      scheme: http
      consistency: default
      dc: dev
      verify: True

The ``driver`` refers to the Consul module, all other options are optional.
For option details see: https://python-consul.readthedocs.io/en/latest/#consul
'''
from __future__ import absolute_import, print_function, unicode_literals

from salt.ext import six
from salt.exceptions import CommandExecutionError

try:
    import consul
    HAS_CONSUL = True
except ImportError:
    HAS_CONSUL = False


__func_alias__ = {
    'set_': 'set'
}

def ensure_str(s, encoding='utf-8', errors='strict'):
    """Coerce *s* to `str`.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if not isinstance(s, (six.text_type, six.binary_type)):
        raise TypeError("not expecting type '%s'" % type(s))
    if six.PY2 and isinstance(s, six.text_type):
        s = s.encode(encoding, errors)
    elif six.PY3 and isinstance(s, six.binary_type):
        s = s.decode(encoding, errors)
    return s

def set_(key, value, profile=None):
    if not profile:
        return False

    conn = get_conn(profile)

    return conn.kv.put(key, value)


def get(key, profile=None):
    if not profile:
        return False

    conn = get_conn(profile)

    _, result = conn.kv.get(key)

    return ensure_str(result['Value']) if result else None


def get_conn(profile):
    '''
    Return a client object for accessing consul
    '''
    params = {}
    for key in ('host', 'port', 'token', 'scheme', 'consistency', 'dc', 'verify'):
        if key in profile:
            params[key] = profile[key]

    if HAS_CONSUL:
        return consul.Consul(**params)
    else:
        raise CommandExecutionError(
            '(unable to import consul, '
            'module most likely not installed. PLease install python-consul)'
        )
