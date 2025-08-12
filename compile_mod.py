# /// script
# requires-python = ">=3.11"
# dependencies = ["rich", "mypy", "typing"]
# ///

import argparse
import os
import subprocess
import sys

from typing import List
from pathlib import Path
from rich import print as rprint

def set_env():
    env = os.environ.copy()
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = "/home/deck/.steam/root/steamapps"
    env["STEAM_COMPAT_DATA_PATH"] = "/home/deck/.steam/root/steamapps/compatdata/573090"
    return env

MOD_COMPILER_CMD = ["/home/deck/.local/share/Steam/steamapps/common/Proton 9.0 (Beta)/proton", "run", "/home/deck/.steam/steam/steamapps/common/Stormworks/sdk/component_mod_compiler.com"]
MESH_COMPILER_CMD = ["/home/deck/.local/share/Steam/steamapps/common/Proton 9.0 (Beta)/proton", "run", "/home/deck/.steam/steam/steamapps/common/Stormworks/sdk/mesh_compiler.com"]

def parse_args(argv: List[str]) -> argparse.Namespace:
    """                                                                                                      
    Parse argv object for CLI arguments.                                                                     
    """                                                                                                      
                                                                                                             
    desc = 'Compiles a SW mod from a definition file'
    epi = f'Example: \n\t{sys.argv[0]} <definition file>'
                                                                                                             
    parser = argparse.ArgumentParser(description=desc, epilog=epi)
    parser.add_argument(
            "definition",
            type=str,
            required=True,
            help='File containing mesh and mod definitions',
    )
                                                                                                             
    args = parser.parse_args(argv)                                                                           
                                                                                                             
    return args

def _compile_mesh(mesh_path: str) -> None:
    rprint(f"Compiling mesh [bold]{mesh_path}[/bold]...")
    base_path = "/".join(mesh_path.split("/")[:-1])
    filename = mesh_path.split("/")[-1].replace(".dae", ".mesh")
    subprocess.run(MESH_COMPILER_CMD + [mesh_path] + ["-o", base_path], env=set_env(), capture_output=True)
    output_path = f"{base_path}/{filename}"
    rprint(f"Successfully compiled mesh: [bold]{output_path}[/bold]")

def _compile_mod(definition: str, assets: List[str]):
    rprint("Compiling mod...")
    result = subprocess.run(MOD_COMPILER_CMD + [definition] + [*assets], env=set_env(), capture_output=True)
    bin_path = definition.replace(".xml", ".bin")
    if os.path.exists(bin_path):
        filename = bin_path.split("/")[-1]
        output_dir = "build/components"
        output_path = f"{output_dir}/{filename}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        Path(bin_path).rename(output_path)
        rprint("Successfully compiled mod with assets:")
        for asset in [definition] + assets:
            rprint(f"  • [bold]{asset}[/bold]")
        rprint(f"Output saved to: [bold]{output_path}[/bold]")
    else:
        rprint("Failed to compile mod.")

def compile(args: argparse.Namespace) -> int:
    result: int = 0
    try:
        definition: str = args.definition
        path = "/".join(definition.split("/")[:-1])
        files = os.listdir(path)
        xml_file = definition

        lua_files = [f"{path}/{x}" for x in files if x.endswith(".lua")]
        ogg_files = [f"{path}/{x}" for x in files if x.endswith(".ogg")]
        dae_files = [f"{path}/{x}" for x in files if x.endswith(".dae")]

        # Compile meshes first
        mesh_files = []
        for dae_file in dae_files:
            _compile_mesh(dae_file)
            mesh_files.append(dae_file.replace('.dae', '.mesh'))

        # Compile the mod itself
        asset_files = mesh_files + lua_files + ogg_files
        _compile_mod(definition=definition, assets=asset_files)
    except:
        result = 1

    return result

if __name__ == '__main__':
    sys.exit(compile(parse_args(sys.argv[1:])))
