#!/usr/bin/env python3

from os import PathLike
from pathlib import Path, PurePath
from typing import List, Union

### Base paths from which other paths derive.  For Steam Deck, uncomment relevant lines and comment the lines below them
USER_HOME_PATH = Path.home()
# STEAM_PATH = "/home/deck/.local/share/Steam" # for Steam Deck
STEAM_PATH = PurePath(USER_HOME_PATH, ".steam/steam")
# STEAM_ROOT_PATH = "/home/deck/.steam/root" # for Steam Deck
STEAM_ROOT_PATH = PurePath(USER_HOME_PATH, ".steam/root")

### Proton-related paths
# PROTON_VERSION = "Proton 9.0 (Beta)" # for Steam Deck
PROTON_VERSION = "Proton 10.0"
PROTON_PATH = PurePath(STEAM_PATH, "steamapps/common", PROTON_VERSION, "proton")

### Stormworks SDK paths
SDK_PATH = PurePath(STEAM_PATH, "steamapps/common/Stormworks/sdk")
MESH_COMPILER_PATH = PurePath(SDK_PATH, "mesh_compiler.com")
MOD_COMPILER_PATH = PurePath(SDK_PATH, "component_mod_compiler.com") 

### Commands to run the two compilers; require set_env from env_config.py to run
MESH_COMPILER_CMD: List[Union[PathLike, str]] = [PROTON_PATH, "run", MESH_COMPILER_PATH]
MOD_COMPILER_CMD: List[Union[PathLike, str]] = [PROTON_PATH, "run", MOD_COMPILER_PATH]
