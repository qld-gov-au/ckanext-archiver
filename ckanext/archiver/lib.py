# encoding: utf-8

import logging
import six

import ckan.plugins as p

from ckanext.archiver.tasks import update_package, update_resource

log = logging.getLogger(__name__)


def compat_enqueue(name, fn, queue, args=None, kwargs=None):
    u'''
    Enqueue a background job using Celery or RQ.
    '''
    try:
        # Try to use RQ
        from ckan.plugins.toolkit import enqueue_job
        nice_name = name + " " + args[1] if (len(args) >= 2) else name
        enqueue_job(fn, args=args, kwargs=kwargs, queue=queue, title=nice_name)
    except ImportError:
        # Fallback to Celery
        import uuid
        from ckan.lib.celery_app import celery
        celery.send_task(name, args=args + [queue], task_id=six.text_type(uuid.uuid4()))


def create_archiver_resource_task(resource, queue):
    if p.toolkit.check_ckan_version(max_version='2.2.99'):
        # earlier CKANs had ResourceGroup
        package = resource.resource_group.package
    else:
        package = resource.package

    compat_enqueue('archiver.update_resource', update_resource, queue, None, {'resource_id': resource.id})

    log.debug('Archival of resource put into queue %s: %s/%s url=%r',
              queue, package.name, resource.id, resource.url)


def create_archiver_package_task(package, queue):
    compat_enqueue('archiver.update_package', update_package, queue, None, {'package_id': package.id})

    log.debug('Archival of package put into queue %s: %s',
              queue, package.name)


def get_extra_from_pkg_dict(pkg_dict, key, default=None):
    for extra in pkg_dict.get('extras', []):
        if extra['key'] == key:
            return extra['value']
    return default
