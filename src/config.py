"""Define a global CONFIG object described by a YAML config file, possibly overriden command-line arguments"""

import argparse

import yaml

_DEFAULT_CONFIG_FILE = "config.yaml"


def _load_yaml_config(file_path):
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def _update_config(config, path, value):
    keys = path.split(".")
    temp_config = config

    UnknownKey = KeyError(f"Unknown configuration key `{path}`")

    for key in keys[:-1]:
        if key in temp_config:
            temp_config = temp_config[key]
        else:
            raise UnknownKey
    if keys[-1] not in temp_config:
        raise UnknownKey
    temp_config[keys[-1]] = value


def _parse_config():
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)

    parser.add_argument(
        "--config-file",
        type=str,
        default=_DEFAULT_CONFIG_FILE,
        help="Path to the YAML configuration file (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        action="append",
        type=str,
        help="Override the --config-file using YAML format, e.g. `--config log.level:INFO`",
    )

    config_args, other_args = parser.parse_known_args()

    config = _load_yaml_config(config_args.config_file)

    if config_args.config:
        for conf_str in config_args.config:
            path, value = conf_str.split(":", 1)
            value = yaml.safe_load(value)
            _update_config(config, path, value)

    return config, parser, other_args


_CONFIG, _CONFIG_PARSER, _OTHER_ARGS = _parse_config()


class ConfigArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs.update(parents=[_CONFIG_PARSER])
        super().__init__(*args, **kwargs)

    def parse_args(self, *args, **kwargs):
        kwargs.update(args=_OTHER_ARGS)
        return super().parse_args(*args, **kwargs)


class YAMLDict(dict):
    def __call__(self, path):
        """Return the value at the given path, eg. `CONFIG("log.level")` maps to `CONFIG["log"]["level"]`"""
        keys = path.split(".")
        temp = self

        for key in keys:
            if not isinstance(temp, dict):
                raise KeyError(f"Invalid path `{path}`")
            temp = temp[key]

        return temp


CONFIG = YAMLDict(_CONFIG)