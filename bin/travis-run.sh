#!/bin/sh -e


nosetests --nologcapture --with-pylons=subdir/test-core.ini --with-coverage --cover-package=ckanext.archiver --cover-inclusive --cover-erase --cover-tests
