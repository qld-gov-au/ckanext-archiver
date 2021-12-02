import logging

from ckan import model, plugins
from ckan.tests import helpers as ckan_helpers, factories as ckan_factories

from ckanext.archiver import plugin, model as archiver_model


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

        # add a placeholder modification so the activity stream gets updated
        ckan_helpers.package_patch({'ignore_auth': True}, {'id': pkg.id})
        result = plugin.ArchiverPlugin()._is_it_sufficient_change_to_run_archiver(pkg, 'updated')

        assert result is False, "Expected archival to be skipped"

    def test_link_resource_changed(self):
        pkg = self._test_package()
        pkg.resources[0].url = pkg.resources[0].url + '-updated'
        log.debug("Testing altered package [%s]", pkg)

        # add a placeholder modification so the activity stream gets updated
        ckan_helpers.package_patch({'ignore_auth': True}, {'id': pkg.id})
        result = plugin.ArchiverPlugin()._is_it_sufficient_change_to_run_archiver(pkg, 'updated')

        assert result, "Expected archival to be needed"

    def test_upload_resource_unchanged(self):
        pkg = self._test_package(name="test-archiver-upload", url_type="upload")
        pkg.resources[0].url = pkg.resources[0].url + '-updated'
        log.debug("Testing package with unchanged upload contents [%s]", pkg)

        # add a placeholder modification so the activity stream gets updated
        ckan_helpers.package_patch({'ignore_auth': True}, {'id': pkg.id})
        result = plugin.ArchiverPlugin()._is_it_sufficient_change_to_run_archiver(pkg, 'updated')

        assert result is False, "Expected archival to be skipped"
