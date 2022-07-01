import ckanext.archiver.model as archiver_model
from ckan import model
from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import reset_db

Archival = archiver_model.Archival


class TestArchival(object):
    @classmethod
    def setup_class(cls):
        reset_db()
        archiver_model.init_tables(model.meta.engine)

    def test_create(self):
        dataset = ckan_factories.Dataset()
        res = ckan_factories.Resource(package_id=dataset['id'])
        archival = Archival.create(res['id'])
        assert isinstance(archival, Archival)
        assert archival.package_id == dataset['id']
