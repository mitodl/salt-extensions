# -*- coding: utf-8 -*-
"""
This module exposes the functionality of the TestInfra library
for use with SaltStack in order to verify the state of your minions.
"""
import re
import inspect
import operator
import types

import salt.utils
import logging
log = logging.getLogger(__name__)

try:
    import testinfra
    from testinfra import modules
    TESTINFRA_PRESENT = True
except ImportError:
    log.debug('Unable to import TestInfra')
    TESTINFRA_PRESENT = False

__virtualname__ = 'testinfra'
default_backend = 'local://'
comparisons = {
    'lt': operator.eq,
    'le': operator.le,
    'eq': operator.eq,
    'ne': operator.ne,
    'ge': operator.ge,
    'gt': operator.gt
}


def __virtual__():
    if TESTINFRA_PRESENT:
        return __virtualname__
    return False


def _get_module(module_name, backend=default_backend):
    """Retrieve the correct module implementation determined by the backend
    being used.

    :param module_name: TestInfra module to retrieve
    :param backend: string representing backend for TestInfra
    :returns: desired TestInfra module object
    :rtype: object

    """
    backend_instance = testinfra.get_backend(backend)
    return backend_instance.get_module(_to_pascal_case(module_name))


def _to_pascal_case(snake_case):
    """Convert a snake_case string to its PascalCase equivalent.

    :param snake_case: snake_cased string to be converted
    :returns: PascalCase string
    :rtype: str

    """
    space_case = re.sub('_', ' ', snake_case)
    return re.sub('(^|\s+)([a-z])', lambda match: match.group(2).upper(),
                         space_case)


def _to_snake_case(pascal_case):
    """Convert a PascalCase string to its snake_case equivalent.

    :param pascal_case: PascalCased string to be converted
    :returns: snake_case string
    :rtype: str

    """
    snake_case = re.sub('(^|[a-z])([A-Z])',
                        lambda match: '_{0}'.format(match.group(2).lower()),
                        pascal_case)
    return snake_case.lower().strip('_')


def _get_method_result(module, module_instance, method_name, method_arg=None):
    """Given a TestInfra module object, an instance of that module, and a
    method name, return the result of executing that method against the
    desired module.

    :param module: TestInfra module object
    :param module_instance: TestInfra module instance
    :param method_name: string representing the method to be executed
    :param method_arg: boolean or dictionary object to be passed to method
    :returns: result of executing desired method with supplied argument
    :rtype: variable

    """
    callable = getattr(module, method_name)
    log.debug(callable)
    if isinstance(callable, property):
        result = callable.fget(module_instance)
    else:
        try:
            result = getattr(module_instance,
                             method_name)(method_arg['parameter'])
        except KeyError:
            log.exception('')
    return result


def _apply_assertion(expected, result):
    """Given the result of a method, verify that it matches the expecation.

    This is done by either passing a boolean value as an expecation or a
    dictionary with the expected value and a string representing the desired
    comparison, as defined in the `operator module <https://docs.python.org/2.7/library/operator.html>`_
    (e.g. 'eq', 'ge', etc.).

    :param expected: boolean or dict
    :param result: return value of :ref: `_get_method_result`
    :returns: success or failure state of assertion
    :rtype: bool

    """
    if isinstance(expected, bool):
        return result is expected
    elif isinstance(expected, dict):
        if isinstance(expected['match'], bool):
            return result is expected['match']
        else:
            return comparisons[expected['comparison']](result,
                                                      expected['match'])
    else:
        raise TypeError('Expected bool or dict but received {}'
                        .format(type(expected)))


def run_tests(name, **methods):
    log.debug(name)
    success = True
    msgs = []
    mod_name = methods['__pub_fun'].split('.')[1]
    try:
        mod = _get_module(mod_name)
    except NotImplementedError:
        log.exception('The {} module is not supported on this platform.'
                      .format(module_name))
    modinstance = mod(name)
    methods = {meth_name: methods[meth_name] for meth_name in methods if not
               meth_name.startswith('_')}
    log.debug(methods)
    for meth, arg in methods.items():
        result = _get_method_result(mod, modinstance, meth)
        log.debug(result)
        assertion_result = _apply_assertion(arg, result)
        if not assertion_result:
            success = False
            msgs.append('Assertion failed: {modname} {n} {m} {a}. '
                        'Actual result: {r}'.format(
                            modname=mod_name, n=name, m=meth, a=arg, r=result
                        )
            )
        else:
            msgs.append('Assertion passed:  {modname} {n} {m} {a}. '
                        'Actual result: {r}'.format(
                            modname=mod_name, n=name, m=meth, a=arg, r=result
                        )
            )
    return success, '\n'.join(msgs)


def _copy_function(func, name=None):
    return types.FunctionType(func.__code__,
                              func.__globals__,
                              name or func.__name__,
                              func.__defaults__,
                              func.__closure__)

def _build_doc(module):
    return module.__doc__

for module in modules.__all__:
    mod_func = _copy_function(run_tests)
    mod_func.__doc__ = _build_doc(module)
    globals()[_to_snake_case(module)] = mod_func
