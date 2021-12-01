# encoding: utf-8

from flask import Blueprint

from ckanext.archiver.controllers import archive_download


archival = Blueprint(
    u'archive',
    __name__
)


archival.add_url_rule(
    u'/dataset/<id>/resource/<resource_id>/archive', view_func=archive_download
)


archival.add_url_rule(
    u'/dataset/<id>/resource/<resource_id>/archive/<filename>', view_func=archive_download
)


def get_blueprints():
    return [archival]
