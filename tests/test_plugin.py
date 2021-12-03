# encoding: utf-8

import logging
try:
    from unittest import mock
except ImportError:
    import mock

from ckan import model, plugins
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

    def teardown(self):
        for package_name in ['test-archiver', 'test-archiver-upload']:
            pkg = model.Package.get(package_name)
            if pkg:
                if plugins.toolkit.check_ckan_version(max_version="2.8"):
                    model.repo.new_revision()
                pkg.purge()
                model.repo.commit_and_remove()

    def _test_org(self):
        def load_model_org():
            orgs = model.Session.query(model.Group)\
                .filter(model.Group.type == 'organization')\
                .filter(model.Group.name == 'test-archiver').all()
            if orgs:
                return orgs[0]

        org = load_model_org()
        if not org:
            ckan_factories.Organization(name='test-archiver')
            org = load_model_org()
        return org

    def _test_package(self, name='test-archiver', url='http://example.com', url_type='link', format=None):
        def load_model_package():
            packages = model.Session.query(model.Package)\
                .filter(model.Package.name == name).all()
            if packages:
                return packages[0]

        pkg = load_model_package()
        if not pkg:
            owner_org = self._test_org()
            pkg = {'owner_org': owner_org.id, 'name': name,
                   'resources': [
                       {'url': url + '/' + owner_org.id,
                        'url_type': url_type,
                        'format': format or 'TXT', 'description': 'Test'}
                   ]}
            ckan_helpers.call_action('package_create', **pkg)
            pkg = load_model_package()
        if plugins.toolkit.check_ckan_version(max_version="2.8"):
            model.repo.new_revision()
        model.repo.commit()
        return pkg

    def test_package_unchanged(self):
        pkg = self._test_package()
        log.debug("Testing unchanged package [%s]", pkg)

        with mock.patch('ckanext.archiver.lib.create_archiver_package_task') as create_task:
            # add a placeholder modification so the activity stream gets updated
            ckan_helpers.call_action('package_patch', id=pkg.id)
            create_task.assert_not_called()

    def test_link_resource_changed(self):
        pkg = self._test_package()
        resource = pkg.resources[0]
        log.debug("Testing altered package [%s]", pkg)

        with mock.patch('ckanext.archiver.lib.create_archiver_package_task') as create_task:
            # add a placeholder modification so the activity stream gets updated
            ckan_helpers.call_action('resource_patch', id=resource.id, url=resource.url + '-updated')
            create_task.assert_called_with(pkg, 'priority')

    def test_upload_resource_unchanged(self):
        pkg = self._test_package(name="test-archiver-upload", url_type="upload")
        resource = pkg.resources[0]
        log.debug("Testing package with unchanged upload contents [%s]", pkg)

        with mock.patch('ckanext.archiver.lib.create_archiver_package_task') as create_task:
            # add a placeholder modification so the activity stream gets updated
            ckan_helpers.call_action('resource_patch', id=resource.id)
            create_task.assert_not_called()
