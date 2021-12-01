# encoding: utf-8

import click
from .command_functions import ArchivalCommands


# Click commands for CKAN 2.9 and above


@click.group(short_help='Download and save copies of all package resources.')
def archiver():
    '''Archiver commands
    '''
    pass


@archiver.command()
def init():
    '''Creates the database table archiver needs to run.
    '''
    ArchivalCommands().initdb()


@archiver.command()
def migrate():
    '''Updates the database schema to include new fields.
    '''
    ArchivalCommands().migrate()


@archiver.command()
@click.option('-q', '--queue', help='Send to a particular queue')
@click.argument(u'dataset-spec', nargs=-1)
def update(dataset_spec, queue=None):
    '''Archive all resources or just those belonging to a specific
    package or group, if specified
    '''
    ArchivalCommands().update(dataset_spec, queue)


@archiver.command()
@click.option('-q', '--queue', help='Send to a particular queue')
@click.argument(u'dataset-spec', nargs=-1)
def update_test(dataset_spec, queue=None):
    '''Does an archive in the current process i.e. avoiding worker queue
    so that you can test on the command-line more easily.
    '''
    ArchivalCommands(queue).update_test(dataset_spec)


@archiver.command()
def clean_status():
    '''Cleans the TaskStatus records that contain the status of each
     archived resource, whether it was successful or not, with errors.
     It does not change the cache_url etc. in the Resource
    '''
    ArchivalCommands().clean_status()


@archiver.command()
def clean_cached_resources():
    '''Removes all cache_urls and other references to resource files on disk.
    '''
    ArchivalCommands().clean_cached_resources()


@archiver.command()
@click.argument(u'dataset_spec')
def view(dataset_spec):
    '''Views archival info, in general and if you specify one, about
    a particular dataset's resources.
    '''
    ArchivalCommands().view(dataset_spec)


@archiver.command()
@click.argument(u'outputfile')
def report(outputfile):
    '''Generates a report on orphans, either resources where the path
    does not exist, or files on disk that don't have a corresponding
    orphan. The outputfile parameter is the name of the CSV output
    from running the report.
    '''
    ArchivalCommands.report(outputfile, False)


@archiver.command()
@click.argument(u'outputfile')
def delete_orphans(outputfile):
    '''Deletes orphans that are files on disk with no corresponding
    resource. This uses the report command and will write out a
    report to [outputfile]
    Does not cleanup IUploader plugin uploaded files as they may not be
    on disk.
    '''
    ArchivalCommands().report(outputfile, True)


@archiver.command()
def migrate_archive_dirs():
    '''Migrate the layout of the archived resource directories.
    Previous versions of ckanext-archiver stored resources on disk
    at: {resource-id}/filename.csv and this version puts them at:
    {2-chars-of-resource-id}/{resource-id}/filename.csv
    Running this moves them to the new locations and updates the
    cache_url on each resource to reflect the new location.
    '''
    ArchivalCommands().migrate_archive_dirs()


@archiver.command()
def size_report():
    '''Reports on the sizes of files archived.
    '''
    ArchivalCommands().size_report()


@archiver.command()
def delete_files_larger_than_max():
    '''For when you reduce the ckanext-archiver.max_content_length and
    want to delete archived files that are now above the threshold,
    and stop referring to these files in the Archival table of the db.
    '''
    ArchivalCommands().delete_files_larger_than_max_content_length()


def get_commands():
    return [archiver]
