# -*- coding: utf-8 -*-
'''
Connection module for Amazon CloudFront

.. versionadded:: develop

:depends: boto3

:configuration: This module accepts explicit AWS credentials but can also
    utilize IAM roles assigned to the instance through Instance Profiles or
    it can read them from the ~/.aws/credentials file or from these
    environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.
    Dynamic credentials are then automatically obtained from AWS API and no
    further configuration is necessary. More information available at:

    .. code-block:: text

        http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/
            iam-roles-for-amazon-ec2.html

        http://boto3.readthedocs.io/en/latest/guide/
            configuration.html#guide-configuration

    If IAM roles are not used you need to specify them either in a pillar or
    in the minion's config file:

    .. code-block:: yaml

        cloudfront.keyid: GKTADJGHEIQSXMKKRBJ08H
        cloudfront.key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs

    A region may also be specified in the configuration:

    .. code-block:: yaml

        cloudfront.region: us-east-1

    If a region is not specified, the default is us-east-1.

    It's also possible to specify key, keyid and region via a profile, either
    as a passed in dict, or as a string to pull from pillars or minion config:

    .. code-block:: yaml

        myprofile:
            keyid: GKTADJGHEIQSXMKKRBJ08H
            key: askdjghsdfjkghWupUjasdflkdfklgjsdfjajkghs
            region: us-east-1
'''
# keep lint from choking on _get_conn and _cache_id
# pylint: disable=E0602

# Import Python libs
from __future__ import absolute_import
import logging

# Import Salt libs
import salt.ext.six as six
from salt.utils.odict import OrderedDict

import yaml

# Import third party libs
try:
    # pylint: disable=unused-import
    import boto3
    import botocore
    # pylint: enable=unused-import
    logging.getLogger('boto3').setLevel(logging.CRITICAL)
    HAS_BOTO = True
except ImportError:
    HAS_BOTO = False

log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load if boto3 libraries exist.
    '''
    if not HAS_BOTO:
        return False
    __utils__['boto3.assign_funcs'](__name__, 'cloudfront')
    return True


def _list_distributions(
    conn,
    name=None,
    region=None,
    key=None,
    keyid=None,
    profile=None,
):
    '''
    Private function that returns an iterator over all CloudFront distributions.
    The caller is responsible for all boto-related error handling.

    name
        (Optional) Only yield the distribution with the given name
    '''
    for dl in conn.get_paginator('list_distributions').paginate():
        if 'Items' not in dl['DistributionList']:
            # If there are no items, AWS omits the `Items` key for some reason
            continue
        for partial_dist in dl['DistributionList']['Items']:
            tags = conn.list_tags_for_resource(Resource=partial_dist['ARN'])
            tags = dict((kv['Key'], kv['Value']) for kv in tags['Tags']['Items'])

            id_ = partial_dist['Id']
            if 'Name' not in tags:
                log.warning(
                    'CloudFront distribution {0} has no Name tag.'.format(id_),
                )
                continue
            d_name = tags.pop('Name', None)
            if name is not None and d_name != name:
                continue

            # NOTE: list_distributions() returns a DistributionList,
            # which nominally contains a list of Distribution objects.
            # However, they are mangled in that they are missing values
            # (`Logging`, `ActiveTrustedSigners`, and `ETag` keys)
            # and moreover flatten the normally nested DistributionConfig
            # attributes to the top level.
            # Hence, we must call get_distribution() to get the full object,
            # and we cache these objects to help lessen API calls.
            distribution = _cache_id(
                'cloudfront',
                sub_resource=d_name,
                region=region,
                key=key,
                keyid=keyid,
                profile=profile,
            )
            if distribution:
                yield (d_name, distribution)
                continue

            dist_with_etag = conn.get_distribution(Id=id_)
            distribution = {
                'distribution': dist_with_etag['Distribution'],
                'etag': dist_with_etag['ETag'],
                'tags': tags,
            }
            _cache_id(
                'cloudfront',
                sub_resource=d_name,
                resource_id=distribution,
                region=region,
                key=key,
                keyid=keyid,
                profile=profile,
            )
            yield (d_name, distribution)


def get_distribution(name, region=None, key=None, keyid=None, profile=None):
    '''
    Get information about a CloudFront distribution (configuration, tags) with a given name.

    name
        Name of the CloudFront distribution

    region
        Region to connect to

    key
        Secret key to use

    keyid
        Access key to use

    profile
        A dict with region, key, and keyid,
        or a pillar key (string) that contains such a dict.

    CLI Example::

    .. code-block:: bash

        salt myminion boto_cloudfront.get_distribution name=mydistribution profile=awsprofile

    '''
    distribution = _cache_id(
        'cloudfront',
        sub_resource=name,
        region=region,
        key=key,
        keyid=keyid,
        profile=profile,
    )
    if distribution:
        return {'result': distribution}

    conn = _get_conn(region=region, key=key, keyid=keyid, profile=profile)
    try:
        for _, d in _list_distributions(
            conn,
            name=name,
            region=region,
            key=key,
            keyid=keyid,
            profile=profile,
        ):
            # _list_distributions should only return the one distribution
            # that we want (with the given name).
            # In case of multiple distributions with the same name tag,
            # our use of caching means list_distributions will just
            # return the first one over and over again,
            # so only the first result is useful.
            if distribution is not None:
                msg = 'More than one distribution found with name {0}'.format(
                    name
                )
                return {'error': msg}
            distribution = d
    except botocore.exceptions.ClientError as e:
        return {'error': __utils__['boto3.get_error'](e)}
    if not distribution:
        return {'result': None}

    _cache_id(
        'cloudfront',
        sub_resource=name,
        resource_id=distribution,
        region=region,
        key=key,
        keyid=keyid,
        profile=profile,
    )
    return {'result': distribution}


def export_distributions(region=None, key=None, keyid=None, profile=None):
    '''
    Get details of all CloudFront distributions.
    Produces results that can be used to create an SLS file.

    CLI Example:

        salt-call boto_cloudfront.export_distributions --out=txt |\
            sed "s/local: //" > cloudfront_distributions.sls
    '''
    results = OrderedDict()
    conn = _get_conn(region=region, key=key, keyid=keyid, profile=profile)
    try:
        for name, distribution in _list_distributions(
            conn,
            region=region,
            key=key,
            keyid=keyid,
            profile=profile,
        ):
            config = distribution['distribution']['DistributionConfig']
            tags = distribution['tags']

            distribution_sls_data = [
                {'name': name},
                {'config': config},
                {'tags': tags},
            ]
            results['Manage CloudFront distribution {0}'.format(name)] = {
                'boto_cloudfront.present': distribution_sls_data,
            }
    except botocore.exceptions.ClientError as e:
        # Raise an exception, as this is meant to be user-invoked at the CLI
        # as opposed to being called from execution or state modules
        raise e

    dumper = __utils__['yamldumper.get_dumper']('IndentedSafeOrderedDumper')
    return yaml.dump(
        results,
        default_flow_style=False,
        Dumper=dumper,
    )


def create_distribution(
    name,
    config,
    tags=None,
    region=None,
    key=None,
    keyid=None,
    profile=None,
):
    '''
    Create a CloudFront distribution with the given name, config, and (optionally) tags.

    name
        Name for the CloudFront distribution

    config
        Configuration for the distribution

    tags
        Tags to associate with the distribution

    region
        Region to connect to

    key
        Secret key to use

    keyid
        Access key to use

    profile
        A dict with region, key, and keyid,
        or a pillar key (string) that contains such a dict.
    '''
    if tags is None:
        tags = {}
    if 'Name' in tags:
        # Be lenient and silently accept if names match, else error
        if tags['Name'] != name:
            return {'error': 'Must not pass `Name` in `tags` but as `name`'}
    tags['Name'] = name
    tags = {
        'Items': [{'Key': k, 'Value': v} for k, v in six.iteritems(tags)]
    }

    conn = _get_conn(region=region, key=key, keyid=keyid, profile=profile)
    try:
        conn.create_distribution_with_tags(
            DistributionConfigWithTags={
                'DistributionConfig': config,
                'Tags': tags,
            },
        )
        _cache_id(
            'cloudfront',
            sub_resource=name,
            invalidate=True,
            region=region,
            key=key,
            keyid=keyid,
            profile=profile,
        )
    except botocore.exceptions.ClientError as e:
        return {'error': __utils__['boto3.get_error'](e)}

    return {'result': True}


def update_distribution(
    name,
    config,
    tags=None,
    region=None,
    key=None,
    keyid=None,
    profile=None,
):
    '''
    Update the config (and optionally tags) for the CloudFront distribution with the given name.

    name
        Name of the CloudFront distribution

    config
        Configuration for the distribution

    tags
        Tags to associate with the distribution

    region
        Region to connect to

    key
        Secret key to use

    keyid
        Access key to use

    profile
        A dict with region, key, and keyid,
        or a pillar key (string) that contains such a dict.
    '''
    r = get_distribution(
        name,
        region=region,
        key=key,
        keyid=keyid,
        profile=profile
    )
    if 'error' in r:
        return r
    r = r['result']

    distribution = r['distribution']
    id_ = distribution['Id']
    arn = distribution['ARN']
    d_config = distribution['DistributionConfig']
    config_diff = __utils__['dictdiffer.deep_diff'](d_config, config)
    if tags:
        tags_diff = __utils__['dictdiffer.deep_diff'](r['tags'], tags)

    conn = _get_conn(region=region, key=key, keyid=keyid, profile=profile)
    try:
        if 'old' in config_diff or 'new' in config_diff:
            conn.update_distribution(
                DistributionConfig=config,
                Id=id_,
                IfMatch=r['etag'],
            )
        if tags:
            if 'new' in tags_diff:
                tags_to_add = {
                    'Items': [
                        {'Key': k, 'Value': v}
                        for k, v in six.iteritems(tags_diff['new'])
                    ],
                }
                conn.tag_resource(
                    Resource=arn,
                    Tags=tags_to_add,
                )
            if 'old' in tags_diff:
                tags_to_remove = {
                    'Items': list(tags_diff['old'].keys()),
                }
                conn.untag_resource(
                    Resource=arn,
                    TagKeys=tags_to_remove,
                )
    except botocore.exceptions.ClientError as e:
        return {'error': __utils__['boto3.get_error'](e)}
    finally:
        _cache_id(
            'cloudfront',
            sub_resource=name,
            invalidate=True,
            region=region,
            key=key,
            keyid=keyid,
            profile=profile,
        )

    return {'result': True}
