from salttesting import TestCase
from extensions._modules import testinframod


class TestinframodTestCase(TestCase):

    def test_to_pascal_case(self):
        for testinput, expected in [
                ('file', 'File'),
                ('system_info', 'SystemInfo'),
                ('Package', 'Package'),
                ('camelCase', 'CamelCase'),
                ('Pascal_With_Underscores', 'PascalWithUnderscores')]:
            self.assertEqual(testinframod._to_pascal_case(testinput), expected)


    def test_to_snake_case(self):
        for testinput, expected in [
                ('File', 'file'),
                ('SystemInfo', 'system_info'),
                ('package', 'package'),
                ('camelCase', 'camel_case'),
                ('Pascal_With_Underscores', 'pascal_with_underscores'),
                ('Pascal_WithUnderscore', 'pascal_with_underscore')]:
            self.assertEqual(testinframod._to_snake_case(testinput), expected)


    def test_get_method_result_for_property(self):
        module_name = 'file'
        method_name = 'is_file'
        module = testinframod._get_module(module_name)
        module_instance = module(__file__)
        self.assertTrue(testinframod._get_method_result(module,
                                                        module_instance,
                                                        method_name))


    def test_get_method_result_for_function(self):
        module_name = 'file'
        method_name = 'contains'
        method_arg = {'parameter': 'import testinframod'}
        module = testinframod._get_module(module_name)
        module_instance = module(__file__)
        self.assertTrue(testinframod._get_method_result(module,
                                                        module_instance,
                                                        method_name,
                                                        method_arg))


    def test_get_method_result_for_missing_function(self):
        module_name = 'file'
        method_name = 'no_such_method'
        method_arg = {'parameter': 'import testinframod'}
        module = testinframod._get_module(module_name)
        module_instance = module(__file__)
        self.assertRaises(testinframod.InvalidArgumentError,
                          testinframod._get_method_result,
                          module,
                          module_instance,
                          method_name,
                          method_arg)


    def test_get_method_result_for_missing_argument_key(self):
        module_name = 'file'
        method_name = 'no_such_method'
        method_arg = {}
        module = testinframod._get_module(module_name)
        module_instance = module(__file__)
        self.assertRaises(testinframod.InvalidArgumentError,
                          testinframod._get_method_result,
                          module,
                          module_instance,
                          method_name,
                          method_arg)


    def test_apply_assertion(self):
        cases = [
            ({'expected': True, 'result': True}, True),
            ({'expected': True, 'result': False}, False),
            ({'expected': False, 'result': True}, False),
            ({'expected': {'expected': True, 'comparison': 'is_'},
              'result': True}, True),
            ({'expected': {'expected': False, 'comparison': 'is_'},
              'result': True}, False),
            ({'expected': {'expected': True, 'comparison': 'is_'},
              'result': False}, False),
            ({'expected': {'expected': 'test_string', 'comparison': 'eq'},
              'result': 'test_string'}, True),
            ({'expected': {'expected': 'test_string', 'comparison': 'eq'},
              'result': 'foo_string'}, False),
            ({'expected': {'expected': 'test_string', 'comparison': 'ne'},
              'result': 'foo_string'}, True),
            ({'expected': {'expected': 1, 'comparison': 'eq'},
              'result': 1}, True),
            ({'expected': {'expected': 1, 'comparison': 'eq'},
              'result': 2}, False),
            ({'expected': {'expected': 1, 'comparison': 'gt'},
              'result': 2}, True),
            ({'expected': {'expected': 1, 'comparison': 'ge'},
              'result': 2}, True),
            ({'expected': {'expected': 1, 'comparison': 'gt'},
              'result': 1}, False),
            ({'expected': {'expected': 2, 'comparison': 'lt'},
              'result': 1}, True),
            ({'expected': {'expected': 2, 'comparison': 'le'},
              'result': 1}, True),
        ]
        for case in cases:
            self.assertEqual(
                testinframod._apply_assertion(case[0]['expected'],
                                              case[0]['result']),
                case[1], str(case))


    def test_run_tests(self):
        pass


    def test_copy_function(self):
        new_func = testinframod._copy_function('package', name='foo_func')
        self.assertEqual(str(new_func.__closure__[0].cell_contents),
                         str('package'))
