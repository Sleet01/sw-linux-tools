#!/usr/bin/env python3

import os

from os import PathLike
from pathlib import Path, PurePath

from constants import STEAM_ROOT_PATH

ROOT_STEAMAPPS_PATH = PurePath(STEAM_ROOT_PATH, "steamapps")
ROOT_STORMWORKS_PATH = PurePath(STEAM_ROOT_PATH, "steamapps/compatdata/573090")

def set_env():
    """This function configures the environment for proton to run apps outside of steam via the command line"""

    env = os.environ.copy()
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = ROOT_STEAMAPPS_PATH
    env["STEAM_COMPAT_DATA_PATH"] = ROOT_STORMWORKS_PATH
    return env
