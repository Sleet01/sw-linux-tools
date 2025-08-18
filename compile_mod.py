#!/usr/bin/env python3

# /// script
# requires-python = ">=3.11"
# dependencies = ["rich"]
# ///

# sleet01
# all credit to sprrk for their prior work

import argparse
import os
import subprocess
import sys

from typing import List
from pathlib import Path
from rich import print as rprint
from rich.pretty import pprint

from constants import (
    MESH_COMPILER_CMD,
    MOD_COMPILER_CMD
)

from env_config import set_env


class ValidateDefinitionFile(argparse.Action):
    """Verify that project dir exists and contains required files"""
    def __call__(self, parser, namespace, values, option_string=None):
        path = Path(values)
        if (values == '') or not (path.exists() and path.is_file()):
            print("Provided path:", values)
            raise argparse.ArgumentError(self, 'Not a valid definition file.')
        # Should also validate that all required contents are present here
        setattr(namespace, self.dest, values)


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
        action=ValidateDefinitionFile,
        help='Path to file containing mod definition',
    )
                                                                                                             
    args = parser.parse_args(argv)                                                                           
                                                                                                             
    return args


def _compile_mesh(mesh_path: str) -> None:
    rprint(f"Compiling mesh [bold]{mesh_path}[/bold]...")
    filename = mesh_path.replace(".dae", ".mesh")
    result = subprocess.run(MESH_COMPILER_CMD + [mesh_path] + ["-o", "./"], env=set_env(), capture_output=True)
    if os.path.exists(filename):
        rprint(f"Successfully compiled mesh: [bold]{filename}[/bold]")
    else:
        rprint("Failed to compile mesh.")
        rprint(f"Args: {result.args}")
        rprint(f"Exit code: {result.returncode}")
        rprint(f"stdout: {str(result.stdout, 'utf-8')}")
        rprint(f"stderr: {str(result.stderr, 'utf-8')}")

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
        rprint(f"Output saved to: [bold]./{output_path}[/bold]")
        return 0
    else:
        rprint("Failed to compile mod.")
        rprint(f"Args: {result.args}")
        rprint(f"Exit code: {result.returncode}")
        rprint(f"stdout: {str(result.stdout, 'utf-8')}")
        rprint(f"stderr: {str(result.stderr, 'utf-8')}")
        return result.returncode


def compile(args: argparse.Namespace) -> int:
    result: int = 0
    try:
        definition: str = args.definition

        # Get path to definition file
        path = os.path.dirname(definition)
        files = os.listdir(path)

        # All asset paths have to omit paths; for this reason, files must be in the
        # definition file's directory
        lua_files = [f"{x}" for x in files if x.endswith(".lua")]
        ogg_files = [f"{x}" for x in files if x.endswith(".ogg")]
        dae_files = [f"{x}" for x in files if x.endswith(".dae")]
        txtr_files = [f"{x}" for x in files if x.endswith(".txtr")]

        # Compile meshes first; update file listing afterward
        for dae_file in dae_files:
            _compile_mesh(dae_file)
            files = os.listdir(path)

        # Collect mesh files
        mesh_files = [f"{x}" for x in files if x.endswith(".mesh")]

        # Compile the mod itself
        asset_files = mesh_files + txtr_files + lua_files + ogg_files
        result = _compile_mod(definition=definition, assets=asset_files)
    except Exception as e:
        rprint(f"Error: {str(e)}")
        result = 1

    return result

if __name__ == '__main__':
    sys.exit(compile(parse_args(sys.argv[1:])))
