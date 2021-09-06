import importlib

import pluggy

from . import hookspecs

DEFAULT_PLUGINS = ("d2b.internal_plugins.core", "d2b.commands.scaffold")

pm = pluggy.PluginManager("d2b")
pm.add_hookspecs(hookspecs)

# load plugins
pm.load_setuptools_entrypoints("d2b")
for plugin in DEFAULT_PLUGINS:
    mod = importlib.import_module(plugin)
    pm.register(mod, plugin)


def get_plugins():
    plugins = []
    plugin_to_distinfo = dict(pm.list_plugin_distinfo())
    for plugin in pm.get_plugins():
        hook_callers = pm.get_hookcallers(plugin)
        if hook_callers is None:
            continue
        plugin_info = {
            "name": plugin.__name__,
            "hooks": [h.name for h in hook_callers],
        }
        distinfo = plugin_to_distinfo.get(plugin)
        if distinfo:
            plugin_info["version"] = distinfo.version
            plugin_info["name"] = distinfo.project_name
        plugins.append(plugin_info)
    return plugins
