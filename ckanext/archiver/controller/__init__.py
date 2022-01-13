# encoding: utf-8

import os
from six.moves.urllib import parse as urlparse

from ckan import model
from ckan.common import _, c
from ckan.lib import uploader
import ckantoolkit as toolkit


def archive_download(id, resource_id, filename=None):
    """
    Provides a direct download by either redirecting the user to the url
    stored or downloading an uploaded file directly.
    """
    context = {'model': model, 'session': model.Session,
               'user': c.user, 'auth_user_obj': c.userobj}

    try:
        resource = toolkit.get_action('resource_show')(context, {'id': resource_id})
        # Quick auth check to ensure you can access this resource
        toolkit.check_access('package_show', context, {'id': id})
    except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
        toolkit.abort(404, _('Resource not found'))

    # Archived files are only links not uploads
    if resource.get('url_type') != 'upload':

        # Return the key used for this resource in storage.
        #
        # Keys are in the form:
        # <uploaderpath>/<upload_to>/<2 char from resource id >/<resource id>/<filename>
        #
        # e.g.:
        # my_storage_path/archive/16/165900ba-3c60-43c5-9e9c-9f8acd0aa93f/data.csv
        relative_archive_path = os.path.join(resource['id'][:2], resource['id'])

        # try to get a file name from the url
        parsed_url = urlparse.urlparse(resource.get('url'))
        try:
            file_name = parsed_url.path.split('/')[-1] or 'resource'
            file_name = file_name.strip()  # trailing spaces cause problems
            file_name = file_name.encode('ascii', 'ignore')  # e.g. u'\xa3' signs
        except Exception:
            file_name = "resource"

        try:
            upload = uploader.get_uploader(os.path.join('archive', relative_archive_path))
            return upload.download(file_name)
        except OSError:
            # includes FileNotFoundError
            toolkit.abort(404, _('Resource data not found'))
    toolkit.abort(404, _('No download is available'))
