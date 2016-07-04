import os
from invoke import task


PYTHON_PATH = '../env/bin/python'


# not to be formatted
PLUGIN_TEMPLATE = """{% load cms_tags %}

{# wrap the child plugins in some element or use as it is. #}
{% for plugin in instance.child_plugin_instances %}
    {% render_plugin plugin %}
{% endfor %}
"""


MODEL_IMPORTS = """from cms.models import CMSPlugin
from cms.utils.compat.dj import python_2_unicode_compatible
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
"""

MODEL = """@python_2_unicode_compatible
class {plugin_model_class}(CMSPlugin):

    def __str__(self):
        return self.__class__.__name__
"""


CMS_PLUGIN_IMPORTS = """from cms.models import CMSPlugin
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool
from django.utils.translation import ugettext_lazy as _

from .models import {plugin_model_class}
"""

CMS_PLUGIN = """class {plugin_class}(CMSPluginBase):
    model = {plugin_model_class}
    module = _("{cms_plugin_module_name}")
    name = _("{cms_plugin_name}")
    render_template = "{plugin_template_path}"
    # allow_children = True

    def render(self, context, instance):
        context.update({{
            'instance': instance,
        }})
        return context
"""


def exclude_suffix(string, suffix):
    if string.endswith(suffix):
        return string[:-len(suffix)]
    return string


@task(help={'plugin-name': "Required. Name of the plugin to be created."})
def startplugin(ctx, plugin_name):
    """
    Create django-cms plugin with given name.
    """
    if not plugin_name:
        raise ValueError("Plugin name must be specified")
    
    django_app_name = exclude_suffix(plugin_name.lower(), "plugin").strip("_")  # snake_case without 'plugin' suffix

    if django_app_name.find("_") == -1:
        cms_plugin_name = django_app_name.title()
        plugin_model_class = cms_plugin_name
    else:
        cms_plugin_name = django_app_name.replace("_", " ").title()
        plugin_model_class = cms_plugin_name.replace(" ", "")

    plugin_class = "{}Plugin".format(plugin_model_class)
    plugin_template_path = "{0}/{0}.html".format(django_app_name)

    # create django app
    ctx.run('{} manage.py startapp {}'.format(PYTHON_PATH, django_app_name))

    with open("{}/models.py".format(django_app_name), "w+") as plugin_models_file:
        plugin_models_file.write(MODEL_IMPORTS)
        plugin_models_file.write("\n\n")
        plugin_models_file.write(MODEL.format(plugin_model_class=plugin_model_class))

    with open("{}/cms_plugins.py".format(django_app_name), "w+") as plugin_cms_plugins_file:
        plugin_cms_plugins_file.write(CMS_PLUGIN_IMPORTS.format(plugin_model_class=plugin_model_class))
        plugin_cms_plugins_file.write("\n\n")
        plugin_cms_plugins_file.write(CMS_PLUGIN.format(
            plugin_class=plugin_class,
            plugin_model_class=plugin_model_class,
            cms_plugin_module_name=cms_plugin_name,
            cms_plugin_name=cms_plugin_name,
            plugin_template_path=plugin_template_path
            ))

    plugin_template_file_path = "{}/templates/{}".format(django_app_name, plugin_template_path)
    if not os.path.exists(os.path.dirname(plugin_template_file_path)):
        try:
            os.makedirs(os.path.dirname(plugin_template_file_path))
        except OSError as ex: # Protect against race condition
            if ex.errno != errno.EEXIST:
                raise
    with open(plugin_template_file_path, "w+") as plugin_template_file:
        plugin_template_file.write(PLUGIN_TEMPLATE)