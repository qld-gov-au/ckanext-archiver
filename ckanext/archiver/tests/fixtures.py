import pytest

from ckan import plugins

from ckanext.archiver.tests.mock_flask_server import create_app

import threading


@pytest.fixture(scope='session', autouse=True)
def client():
    app = create_app()
    port = 9091
    thread = threading.Thread(target=lambda: app.run(debug=True, port=port, use_reloader=False))
    thread.daemon = True
    thread.start()

    yield "http://127.0.0.1:" + str(port)


@pytest.fixture(autouse=True)
def migrate_activity_db(migrate_db_for):
    if plugins.toolkit.check_ckan_version('2.11'):
        migrate_db_for('activity')
