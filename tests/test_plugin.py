import logging

from ckan import model
try:
    from ckan.tests import helpers as ckan_helpers
    from ckan.tests import factories as ckan_factories
    from ckan.tests.legacy import BaseCase
except ImportError:
    from ckan.tests import helpers as ckan_helpers
    from ckan.new_tests import factories as ckan_factories
    from ckan.tests import BaseCase

from ckanext.archiver import plugin, model as archiver_model


# enable celery logging for when you run nosetests -s
log = logging.getLogger('ckanext.archiver.plugin')


def get_logger():
    return log


class TestArchiver(BaseCase):
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
                model.repo.new_revision()
                pkg.purge()
                model.repo.commit_and_remove()

    def _test_org(self):
        orgs = model.Session.query(model.Group)\
            .filter(model.Group.type == 'organization')\
            .filter(model.Group.name == 'test-archiver').all()
        if orgs:
            return orgs[0]
        else:
            return ckan_factories.Organization(name='test-archiver')

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
            ckan_factories.Dataset(**pkg)
            pkg = load_model_package()
        model.repo.new_revision()
        model.repo.commit()
        return pkg

    def test_package_unchanged(self):
        pkg = self._test_package()
        result = plugin.ArchiverPlugin()._is_it_sufficient_change_to_run_archiver(pkg, 'updated')
        assert result is False, "Expected archival to be skipped"

    def test_link_resource_changed(self):
        pkg = self._test_package()
        pkg.resources[0].url = pkg.resources[0].url + '-updated'
        result = plugin.ArchiverPlugin()._is_it_sufficient_change_to_run_archiver(pkg, 'updated')
        assert result, "Expected archival to be needed"

    def test_upload_resource_unchanged(self):
        pkg = self._test_package(name="test-archiver-upload", url_type="upload")
        if hasattr(pkg, 'resources'):
            pkg.resources[0].url = pkg.resources[0].url + '-updated'
        else:
            pkg['resources'][0]['url'] = pkg['resources'][0]['url'] + '-updated'
        result = plugin.ArchiverPlugin()._is_it_sufficient_change_to_run_archiver(pkg, 'updated')
        assert result is False, "Expected archival to be skipped"
