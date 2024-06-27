# encoding: utf-8

import logging

from ckan import model
from ckan import plugins as p

from ckanext.report.interfaces import IReport
from . import helpers, lib
from .interfaces import IPipe
from .logic import action, auth
from .model import Archival, aggregate_archivals_for_a_dataset
from .tasks import notify_package

log = logging.getLogger(__name__)


if p.toolkit.check_ckan_version("2.9"):
    from .plugin_mixins.flask_plugin import MixinPlugin
else:
    from .plugin_mixins.pylons_plugin import MixinPlugin


class ArchiverPlugin(MixinPlugin, p.SingletonPlugin, p.toolkit.DefaultDatasetForm):
    """
    Registers to be notified whenever CKAN resources are created or their URLs
    change, and will create a new ckanext.archiver celery task to archive the
    resource.
    """
    p.implements(p.IDomainObjectModification, inherit=True)
    p.implements(IReport)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IPackageController, inherit=True)

    # IDomainObjectModification

    def notify(self, entity, operation=None):
        if not isinstance(entity, model.Package):
            return

        log.debug('Notified of package event: %s %s', entity.name, operation)

        package_status = self._is_it_sufficient_change_to_run_archiver(entity, operation)
        if package_status:
            log.debug('Creating archiver task: %s', entity.name)
            lib.create_archiver_package_task(entity, 'priority')
        elif package_status is None:
            notify_package({'id': entity.id})

    def _is_it_sufficient_change_to_run_archiver(self, package, operation):
        ''' Returns True if in this revision any of these happened:
        * it is a new dataset
        * dataset licence changed (affects qa)
        * there are resources that have been added or deleted
        * resources have changed their URL or format (affects qa)

        Returns False if the dataset has been deleted, or contains only
        unchanged links.

        Returns None if the no changes were detected, but uploaded files are present.
        This indicates that archival is not needed but downstream processes can still run.
        '''
        if operation == 'new':
            log.debug('New package - will archive')
            # even if it has no resources, QA needs to show 0 stars against it
            return True
        elif operation == 'deleted':
            log.debug('Deleted package - won\'t archive')
            return False
        # therefore operation=changed

        # check to see if resources are added, deleted or URL changed

        # Since 'revisions' is a deprecated feature in CKAN,
        # try to use activity stream to check if dataset changed
        context = {'model': model, 'session': model.Session, 'ignore_auth': True, 'user': None}
        if p.toolkit.check_ckan_version(min_version='2.9.0'):
            data_dict = {'id': package.id, 'limit': 2}

            activity_list = p.toolkit.get_action('package_activity_list')(context, data_dict)
            if len(activity_list) <= 1:
                log.warn('No sign of previous package - will archive anyway')
                return True
            old_act = p.toolkit.get_action('activity_data_show')(context, {'id': activity_list[1]['id']})
            old_pkg_dict = old_act['package']
        else:
            # look for the latest revision
            rev_list = package.all_related_revisions
            if not rev_list:
                log.debug('No sign of previous revisions - will archive')
                return True
            # I am not confident we can rely on the info about the current
            # revision, because we are still in the 'before_commit' stage. So
            # simply ignore that if it's returned.
            if hasattr(model.Session, 'revision') and rev_list[0][0].id == model.Session.revision.id:
                rev_list = rev_list[1:]
            if not rev_list:
                log.warn('No sign of previous revisions - will archive')
                return True
            previous_revision = rev_list[0][0]
            log.debug('Comparing with revision: %s %s',
                      previous_revision.timestamp, previous_revision.id)

            # get the package as it was at that previous revision
            context['revision_id'] = previous_revision.id
            data_dict = {'id': package.id}
            try:
                old_pkg_dict = p.toolkit.get_action('package_show')(
                    context, data_dict)
            except p.toolkit.ObjectNotFound:
                log.warn('No sign of previous package - will archive anyway')
                return True

        # has the licence changed?
        old_licence = (old_pkg_dict['license_id'],
                       lib.get_extra_from_pkg_dict(old_pkg_dict, 'licence')
                       or None)
        new_licence = (package.license_id,
                       package.extras.get('licence') or None)
        if old_licence != new_licence:
            log.debug('Licence has changed - will archive: %r->%r',
                      old_licence, new_licence)
            return True

        # have any resources been added or deleted?
        old_resources = dict((res['id'], res)
                             for res in old_pkg_dict['resources'])
        old_res_ids = set(old_resources.keys())
        new_res_ids = set((res.id for res in package.resources))
        deleted_res_ids = old_res_ids - new_res_ids
        if deleted_res_ids:
            log.debug('Deleted resources - will archive. res_ids=%r',
                      deleted_res_ids)
            return True
        added_res_ids = new_res_ids - old_res_ids
        if added_res_ids:
            log.debug('Added resources - will archive. res_ids=%r',
                      added_res_ids)
            return True

        # have any resources' url/format changed?
        contains_upload = False
        for res in package.resources:
            watched_keys = ['format']
            # Ignore URL changes in uploaded resources.
            # Otherwise we'll end up comparing 'example.txt' to
            # 'http://example.com/dataset/foo/resource/baz/download/example.txt'
            # and thinking that it's changed.
            if res.url_type != 'upload' \
                    or old_resources[res.id]['url_type'] != 'upload':
                watched_keys.append('url')
            for key in watched_keys:
                old_res_value = old_resources[res.id][key]
                new_res_value = getattr(res, key)
                if old_res_value != new_res_value:
                    log.debug('Resource %s changed - will archive. '
                              'id=%s pos=%s url="%s"->"%s"',
                              key, res.id[:4], res.position,
                              old_res_value, new_res_value)
                    return True

            was_in_progress = old_resources[res.id].get('upload_in_progress', None)
            is_in_progress = res.extras.get('upload_in_progress', None)
            if was_in_progress != is_in_progress:
                log.debug('Resource %s upload finished - will archive. ', 'upload_finished')
                return True

            if res.url_type == 'upload':
                contains_upload = True
            log.debug('Resource unchanged. pos=%s id=%s',
                      res.position, res.id[:4])

        if contains_upload:
            log.debug("Unable to confirm new, deleted or changed resources - skip archive, but trigger downstream actions")
            return None
        else:
            log.debug("No new, deleted or changed resources - do not archive")
            return False

    # IReport

    def register_reports(self):
        """Register details of an extension's reports"""
        from ckanext.archiver import reports
        return [reports.broken_links_report_info,
                ]

    # IConfigurer

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')

    # IActions

    def get_actions(self):
        return {
            'archiver_resource_show': action.archiver_resource_show,
            'archiver_dataset_show': action.archiver_dataset_show,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'archiver_resource_show': auth.archiver_resource_show,
            'archiver_dataset_show': auth.archiver_dataset_show,
        }

    # ITemplateHelpers

    def get_helpers(self):
        return dict((name, function) for name, function
                    in helpers.__dict__.items()
                    if callable(function) and name[0] != '_')

    # IPackageController

    def after_show(self, context, pkg_dict):
        """ Old CKAN function name """
        return self.after_dataset_show(context, pkg_dict)

    def after_dataset_show(self, context, pkg_dict):
        # Insert the archival info into the package_dict so that it is
        # available on the API.
        # When you edit the dataset, these values will not show in the form,
        # it they will be saved in the resources (not the dataset). I can't see
        # and easy way to stop this, but I think it is harmless. It will get
        # overwritten here when output again.
        archivals = Archival.get_for_package(pkg_dict['id'])
        if not archivals:
            return

        # dataset
        dataset_archival = aggregate_archivals_for_a_dataset(archivals)
        pkg_dict['archiver'] = dataset_archival

        # resources
        archivals_by_res_id = dict((a.resource_id, a) for a in archivals)
        for res in pkg_dict['resources']:
            archival = archivals_by_res_id.get(res['id'])
            if archival:
                archival_dict = archival.as_dict()
                del archival_dict['id']
                del archival_dict['package_id']
                del archival_dict['resource_id']
                res['archiver'] = archival_dict

    def before_dataset_index(self, pkg_dict):
        '''
        remove `archiver` from index
        '''
        pkg_dict.pop('archiver', None)
        return pkg_dict


class TestIPipePlugin(p.SingletonPlugin):
    """
    """
    p.implements(IPipe, inherit=True)

    def __init__(self, *args, **kwargs):
        self.calls = []

    def reset(self):
        self.calls = []

    def receive_data(self, operation, queue, **params):
        self.calls.append([operation, queue, params])
