"""Make all variables X, Y, Z defined in the .env file available as env.X, env.Y, env.Z, etc.

Note: variables are strings by default, unless they can be evaluated as a Python literal. For example `X=5` in the .env file will result in `env.X == 5` rather than `env.X == "5"`.
"""

import fnmatch as _fnmatch
import os as _os

import dotenv as _dotenv

_ENV_FILES = [".secrets", ".env"]

[_dotenv.load_dotenv(f) for f in _ENV_FILES]


def _parse(value):
    try:
        return eval(value)
    except:  # noqa: E722
        return str(value)


_env_vars = {
    VARIABLE: _parse(
        VALUE := _os.getenv(VARIABLE)
    )  # getenv() enables overriding .env values with system environment variables
    for f in _ENV_FILES
    for VARIABLE in _dotenv.dotenv_values(f).keys()
}

def glob(pattern):
    """Return a dictionary of all dotenv variables that match the given glob pattern"""
    return {k: v for k, v in _env_vars.items() if _fnmatch.fnmatch(k, pattern)}


globals().update(_env_vars)

if __name__ == "__main__":
    print(_env_vars)