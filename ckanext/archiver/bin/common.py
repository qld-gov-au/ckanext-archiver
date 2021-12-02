import ckan
import ckan.plugins as p


def load_config(config_filepath):
    import ckanext.archiver.tasks.load_config as load_config_path
    load_config_path(config_filepath)


def register_translator():
    # Register a translator in this thread so that
    # the _() functions in logic layer can work
    from paste.registry import Registry
    from pylons import translator
    from ckan.lib.cli import MockTranslator
    global registry
    registry = Registry()
    registry.prepare()
    global translator_obj
    translator_obj = MockTranslator()
    registry.register(translator, translator_obj)


def get_resources(state='active', publisher_ref=None, resource_id=None,
                  dataset_name=None):
    ''' Returns all active resources, or filtered by the given criteria. '''
    from ckan import model
    resources = model.Session.query(model.Resource) \
        .filter_by(state=state)
    if p.toolkit.check_ckan_version(max_version='2.2.99'):
        # earlier CKANs had ResourceGroup
        resources = resources.join(model.ResourceGroup)
    resources = resources \
        .join(model.Package) \
        .filter_by(state='active')
    criteria = [state]
    if publisher_ref:
        publisher = model.Group.get(publisher_ref)
        assert publisher
        resources = resources.filter(model.Package.owner_org == publisher.id)
        criteria.append('Publisher:%s' % publisher.name)
    if dataset_name:
        resources = resources.filter(model.Package.name == dataset_name)
        criteria.append('Dataset:%s' % dataset_name)
    if resource_id:
        resources = resources.filter(model.Resource.id == resource_id)
        criteria.append('Resource:%s' % resource_id)
    resources = resources.all()
    print('%i resources (%s)' % (len(resources), ' '.join(criteria)))
    return resources
