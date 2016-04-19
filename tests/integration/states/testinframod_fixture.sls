minion_is_installed:
  testinfra.package:
    - name: salt-minion
    - is_installed: True

minion_is_running:
  testinfra.service:
    - name: salt-minion
    - is_running: True
    - is_enabled: True


file_has_contents:
  testinfra.file:
    - name: /etc/salt/minion
    - exists: True
    - contains:
        parameter: master
        expected: True
        comparison: is_

python_is_v2:
  testinfra.package:
    - name: python
    - is_installed: True
    - version:
        expected: '2.7.9-1'
        comparison: eq
