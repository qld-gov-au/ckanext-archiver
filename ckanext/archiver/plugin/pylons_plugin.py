# encoding: utf-8

from routes.mapper import SubMapper

from ckan import plugins as p


class MixinPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # IRoutes

    def before_map(self, map):
        with SubMapper(map, controller='ckanext.archiver.controller:ArchiverController') as m:
            # Override the resource download links
            m.connect('archive_download',
                      '/dataset/{id}/resource/{resource_id}/archive',
                      action='archive_download')
            m.connect('archive_download',
                      '/dataset/{id}/resource/{resource_id}/archive/{filename}',
                      action='archive_download')
        return map
