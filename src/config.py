import argparse

import yaml


def _load_config(file_path):
    """Load configuration from a YAML file."""
    with open(file_path, "r") as file:
        return yaml.safe_load(file)


def _update_config(config, path, value):
    """Update nested dictionary based on path and value, ensuring the path exists."""
    keys = path.split(".")
    temp_config = config

    keyerror = KeyError(
        f"Invalid configuration key '{path}': not present in configuration file"
    )

    for key in keys[:-1]:
        if key in temp_config:
            temp_config = temp_config[key]
        else:
            raise keyerror
    if keys[-1] not in temp_config:
        raise keyerror
    temp_config[keys[-1]] = value


class ConfigArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_argument(
            "--config-file",
            type=str,
            default=_DEFAULT_CONFIG_FILE,
            help="Path to the YAML configuration file (default: %(default)s)",
        )
        self.add_argument(
            "--config",
            action="append",
            type=str,
            help="Override configuration file using YAML format, e.g. `--config log.level:INFO`",
        )

    def parse_args(self, *fargs, **fkwargs):
        """Monkey-patch to magically update the CONFIG global variable"""
        args = super().parse_args(*fargs, **fkwargs)

        global _CONFIG
        _CONFIG = _load_config(args.config_file)

        # Update configuration if any --config arguments are provided
        if args.config:
            for conf_str in args.config:
                path, value = conf_str.split(":", 1)
                value = yaml.safe_load(value)
                _update_config(_CONFIG, path, value)

        return args


_DEFAULT_CONFIG_FILE = "config.yaml"
_CONFIG = _load_config(_DEFAULT_CONFIG_FILE)


def config():
    global _CONFIG
    return _CONFIG