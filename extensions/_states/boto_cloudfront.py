# -*- coding: utf-8 -*-
'''
Manage CloudFront distributions

.. versionadded:: develop

Create, update and destroy CloudFront distributions.

This module accepts explicit AWS credentials but can also utilize
IAM roles assigned to the instance through Instance Profiles.
Dynamic credentials are then automatically obtained from AWS API
and no further configuration is necessary.
More information available `here
<https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html>`_.

If IAM roles are not used you need to specify them,
either in a pillar file or in the minion's config file:

.. code-block:: yaml

    cloudfront.keyid: GKTADJGHEIQSXMKKRBJ08H
    cloudfront.key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

It's also possible to specify ``key``, ``keyid``, and ``region`` via a profile,
either passed in as a dict, or a string to pull from pillars or minion config:

.. code-block:: yaml

    myprofile:
        keyid: GKTADJGHEIQSXMKKRBJ08H
        key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs
        region: us-east-1

.. code-block:: yaml

    aws:
        region:
            us-east-1:
                profile:
                    keyid: GKTADJGHEIQSXMKKRBJ08H
                    key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs
                    region: us-east-1

:depends: boto3
'''

# Import Python Libs
from __future__ import absolute_import
import difflib
import logging

import yaml

log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load if boto is available.
    '''
    if 'boto_cloudfront.get_distribution' in __salt__:
        return 'boto_cloudfront'
    return False


def present(
    name,
    config,
    tags,
    region=None,
    key=None,
    keyid=None,
    profile=None,
):
    '''
    Ensure the CloudFront distribution is present.

    name (string)
        Name of the CloudFront distribution

    config (dict)
        Configuration for the distribution

    tags (dict)
        Tags to associate with the distribution

    region (string)
        Region to connect to

    key (string)
        Secret key to use

    keyid (string)
        Access key to use

    profile (dict or string)
        A dict with region, key, and keyid,
        or a pillar key (string) that contains such a dict.
    '''
    ret = {
        'name': name,
        'comment': '',
        'changes': {},
    }

    r = __salt__['boto_cloudfront.get_distribution'](
        name,
        region=region,
        key=key,
        keyid=keyid,
        profile=profile,
    )
    if 'error' in r:
        ret['result'] = False
        ret['comment'] = 'Error checking distribution: {0}'.format(r['error'])
        return ret

    old = r['result']
    if old is None:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'Distribution {0} set for creation'.format(name)
            ret['pchanges'] = {'old': None, 'new': name}
            return ret

        r = __salt__['boto_cloudfront.create_distribution'](
            name,
            config,
            tags,
            region=region,
            key=key,
            keyid=keyid,
            profile=profile,
        )
        if 'error' in r:
            ret['result'] = False
            ret['comment'] = 'Error creating distribution: {0}'.format(
                r['error'],
            )
            return ret

        ret['result'] = True
        ret['comment'] = 'Created distribution {0}'.format(name)
        ret['changes'] = {'old': None, 'new': name}
        return ret
    else:
        full_config_old = {
            'config': old['distribution']['DistributionConfig'],
            'tags': old['tags'],
         }
        full_config_new = {
            'config': config,
            'tags': tags,
         }
        diffed_config = __utils__['dictdiffer.deep_diff'](
            full_config_old,
            full_config_new,
        )

        def _yaml_safe_dump(attrs):
            '''Safely dump YAML using a readable flow style'''
            dumper_name = 'IndentedSafeOrderedDumper'
            dumper = __utils__['yamldumper.get_dumper'](dumper_name)
            return yaml.dump(
                attrs,
                default_flow_style=False,
                Dumper=dumper,
            )
        changes_diff = ''.join(difflib.unified_diff(
            _yaml_safe_dump(full_config_old).splitlines(True),
            _yaml_safe_dump(full_config_new).splitlines(True),
        ))

        any_changes = bool('old' in diffed_config or 'new' in diffed_config)
        if not any_changes:
            ret['result'] = True
            ret['coment'] = 'Distribution {0} has correct config'.format(name)
            return ret

        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = '\n'.join([
                'Distribution {0} set for new config:',
                changes_diff,
            ])
            ret['pchanges'] = {'diff': changes_diff}
            return ret

        r = __salt__['boto_cloudfront.update_distribution'](
            name,
            config,
            tags,
            region=region,
            key=key,
            keyid=keyid,
            profile=profile,
        )
        if 'error' in r:
            ret['result'] = False
            ret['comment'] = 'Error updating distribution: {0}'.format(
                r['error'],
            )
            return ret

        ret['result'] = True
        ret['comment'] = 'Updated distribution {0}.'.format(name)
        ret['changes'] = {'diff': changes_diff}
        return ret
