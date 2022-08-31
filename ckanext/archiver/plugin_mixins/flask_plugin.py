# encoding: utf-8

import ckan.plugins as p
from ckanext.archiver import blueprints, cli


class MixinPlugin(p.SingletonPlugin):
    p.implements(p.IBlueprint)
    p.implements(p.IClick)

    # IBlueprint

    def get_blueprint(self):
        return blueprints.get_blueprints()

    # IClick

    def get_commands(self):
        return cli.get_commands()
