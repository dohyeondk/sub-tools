import argparse
import os


class EnvDefault(argparse.Action):
    """
    https://stackoverflow.com/a/10551190
    """

    def __init__(self, env_name, required=True, default=None, **kwargs):
        if env_name:
            if env_name in os.environ:
                default = os.environ[env_name]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
