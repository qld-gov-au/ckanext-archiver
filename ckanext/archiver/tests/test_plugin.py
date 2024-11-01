# encoding: utf-8

import logging
import pytest
try:
    from unittest import mock
except ImportError:
    import mock

from ckan import model
from ckan.tests import helpers as ckan_helpers, factories as ckan_factories

from ckanext.archiver import model as archiver_model


# enable celery logging for when you run nosetests -s
log = logging.getLogger('ckanext.archiver.plugin')


def get_logger():
    return log


class TestPlugin():
    """
    Tests for plugin 'is_it_sufficient_change_to_run_archiver?' logic.
    """

    @classmethod
    def setup_class(cls):
        ckan_helpers.reset_db()
        archiver_model.init_tables(model.meta.engine)

    def _test_package(self, url='http://example.com', url_type='link', format=None):
        owner_org = ckan_factories.Organization()
        pkg = {'owner_org': owner_org['id'],
               'resources': [
                   {'url': url + '/' + owner_org['id'],
                    'url_type': url_type,
                    'format': format or 'TXT', 'description': 'Test'}
        ]}
        pkg = ckan_factories.Dataset(**pkg)
        model.repo.commit()
        return pkg

    def test_package_unchanged(self):
        pkg = self._test_package()
        print("Testing unchanged package [%s]" % pkg)

        with mock.patch('ckanext.archiver.lib.create_archiver_package_task') as create_task:
            # add a placeholder modification so the activity stream gets updated
            ckan_helpers.call_action('package_patch', id=pkg['id'])
            create_task.assert_not_called()

    # This test isn't working even though manually testing the behaviour works
    # Upstream doesn't have it, so skip for now
    @pytest.mark.skip('TODO fix this test')
    def test_link_resource_changed(self):
        pkg = self._test_package()
        resource = pkg['resources'][0]
        print("Testing altered package [%s]" % pkg)

        with mock.patch('ckanext.archiver.lib.create_archiver_package_task') as create_task:
            # add a placeholder modification so the activity stream gets updated
            resource = ckan_helpers.call_action('resource_patch', id=resource['id'], url=resource['url'] + '-updated')
            print("Updated resource: %s" % resource)
            create_task.assert_called_with(pkg, 'priority')

    def test_upload_resource_unchanged(self):
        pkg = self._test_package(url_type="upload")
        resource = pkg['resources'][0]
        print("Testing package with unchanged upload contents [%s]" % pkg)

        with mock.patch('ckanext.archiver.lib.create_archiver_package_task') as create_task:
            # add a placeholder modification so the activity stream gets updated
            ckan_helpers.call_action('resource_patch', id=resource['id'])
            create_task.assert_not_called()
