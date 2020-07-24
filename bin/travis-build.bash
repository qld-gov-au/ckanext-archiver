#!/bin/bash
set -e

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty libcommons-fileupload-java

echo "Installing CKAN and its Python dependencies..."
if [ ! -d ckan ]; then
  git clone https://github.com/$CKAN_GIT_REPO
fi
pushd ckan

#are we building from branch or tag
if [ "${CKAN_BRANCH}dd" == 'dd' ]
then
    CKAN_TAG=$(git tag | grep ^ckan-$CKANVERSION | sort --version-sort | tail -n 1)
    git checkout $CKAN_TAG
    echo "CKAN version: ${CKAN_TAG#ckan-}"
else
    echo "CKAN version: $CKAN_BRANCH"
    git checkout $CKAN_BRANCH
fi

python setup.py develop
if [ -f requirements-py2.txt ]
then
    pip install -r requirements-py2.txt
else
    pip install -r requirements.txt
fi
pip install -r dev-requirements.txt
popd

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Initialising the database..."
pushd ckan
paster db init -c test-core.ini
popd

echo "SOLR config..."
# solr is multicore for tests on ckan master now, but it's easier to run tests
# on Travis single-core still.
# see https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini

#echo "Installing dependency ckanext-report and its requirements..."
#pip install -e git+https://github.com/datagovuk/ckanext-report.git#egg=ckanext-report

echo "Installing ckanext-archiver and its requirements..."
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt

echo "Moving test-core.ini into a subdir..."
mkdir subdir
mv test-core.ini subdir

echo "start solr"
# Fix solr-jetty starting issues https://stackoverflow.com/a/56007895
# https://github.com/Zharktas/ckanext-report/blob/py3/bin/travis-run.bash
sudo mkdir -p /etc/systemd/system/jetty9.service.d
printf "[Service]\nReadWritePaths=/var/lib/solr" | sudo tee /etc/systemd/system/jetty9.service.d/solr.conf
sed '16,21d' /etc/solr/solr-jetty.xml | sudo tee /etc/solr/solr-jetty.xml
sudo systemctl daemon-reload || echo "all good"

printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_ARGS=\"jetty.http.port=8983\"\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty9
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty9 restart

# Wait for jetty9 to start
timeout 20 bash -c 'while [[ "$(curl -s -o /dev/null -I -w %{http_code} http://localhost:8983)" != "200" ]]; do sleep 2;done'



echo "travis-build.bash is done."
