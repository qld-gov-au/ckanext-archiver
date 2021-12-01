# encoding: utf-8

from ckan.plugins import toolkit

from . import archive_download as download_function


class ArchiverController(toolkit.BaseController):

    def archive_download(self, id, resource_id, filename=None):
        return download_function(id, resource_id, filename)
