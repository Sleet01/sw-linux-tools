#!/usr/bin/env python3

# /// script
# requires-python = ">=3.11"
# dependencies = ["rich"]
# ///

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
from rich import print as rprint
from rich.progress import Progress

from constants import (
    MESH_COMPILER_CMD,
    MOD_COMPILER_CMD
)

from env_config import set_env

@dataclass
class Config:
    project_path: str
    output_path: str
    build_name: str

    legacy_meshes_dir: str | None
    legacy_audio_dir: str | None
    legacy_definitions_dir: str | None


def _load_config(project_dir: str) -> Config:
    if project_dir.startswith(".."):
        rprint(f"[red]Error:[/red] Path traversal upwards is not supported.")
        sys.exit(1)

    if project_dir == ".":
        project_path = str(Path.cwd())
    else:
        project_path = os.path.abspath(project_dir)

    config_file = f"{project_path}/modconfig.toml"
    if not Path(config_file).is_file():
        rprint(f"[red]Error:[/red] Config file does not exist.")
        sys.exit(1)

    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    if data.get("legacy", None):
        legacy_meshes_dir = data["legacy"].get("meshes_dir", None)
        legacy_audio_dir = data["legacy"].get("audio_dir", None)
        legacy_definitions_dir = data["legacy"].get("definitions_dir", None)
    else:
        legacy_meshes_dir = None
        legacy_audio_dir = None
        legacy_definitions_dir = None

    build_name = data["build"]["build_name"]
    output_path = f"{project_path}/build/{build_name}"

    return Config(
        project_path=project_path,
        output_path=output_path,
        build_name=build_name,
        legacy_meshes_dir=legacy_meshes_dir,
        legacy_audio_dir=legacy_audio_dir,
        legacy_definitions_dir=legacy_definitions_dir
        )


class ModBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.build_cache_path = f"/tmp/sw-mod-builder/{config.build_name}"

    def _verify_paths(self):
        for filename in ["mod.xml", "mod.png"]:
            file_path = f"{self.config.project_path}/{filename}"
            if not Path(file_path).is_file():
                rprint(f"[red]Error:[/red] File {file_path} does not exist.")
                sys.exit(1)

        data_path = f"{self.config.project_path}/data"
        if not Path().is_dir():
            rprint(f"[red]Error:[/red] Directory {data_path} does not exist.")
            sys.exit(1)

    def _clear_build_cache(self) -> None:
        if Path(self.build_cache_path).is_dir():
            shutil.rmtree(self.build_cache_path)

    def _prepare_build_paths(self) -> None:
        if Path(self.config.output_path).is_dir():
            shutil.rmtree(self.config.output_path)

        Path(f"{self.config.project_path}/build").mkdir(parents=False, exist_ok=True)
        Path(self.config.output_path).mkdir(parents=False, exist_ok=False)
        Path(f"{self.config.output_path}/data").mkdir(parents=False, exist_ok=False)
        Path(f"{self.config.output_path}/data/components").mkdir(parents=False, exist_ok=False)

    async def _compile_mesh(self, filename: str, output_base_path: str) -> Optional[int]:
        cmd = MESH_COMPILER_CMD + [filename] + ["-o", output_base_path]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=set_env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode

    def _copy_assets(self, source_dir: str, target_dir: str, filetype: str) -> None:
        Path(target_dir).mkdir(parents=False, exist_ok=False)
        for filename in os.listdir(source_dir):
            if filename.endswith(filetype):
                shutil.copy(f"{source_dir}/{filename}", f"{target_dir}/{filename}")

    async def _build_legacy(self) -> None:
        legacy_meshes_dir = f"{self.config.project_path}/src/legacy/meshes"
        if Path(legacy_meshes_dir).is_dir():
            mesh_build_path = f"/tmp/sw-mod-builder/{self.config.build_name}/build/meshes"
            Path(mesh_build_path).mkdir(parents=True, exist_ok=True)

            rprint("Compiling legacy mesh assets...")
            dae_files = [x for x in os.listdir(legacy_meshes_dir) if x.endswith(".dae")]
            tasks = []
            with Progress(transient=True) as progress:
                progress_task = progress.add_task("Compiling meshes...", total=len(dae_files))
                for filename in dae_files:
                    task = asyncio.create_task(self._compile_mesh(filename=f"{legacy_meshes_dir}/{filename}", output_base_path=mesh_build_path), name=filename)
                    tasks.append(task)

                # MyPy has a bug where it cannot find a matching type between async iterators and generators, despite this working explicitly as intended
                async for task in asyncio.as_completed(tasks): # type: ignore[attr-defined]
                    progress.console.print(f"Compiled mesh: [yellow]{task.get_name()}[/yellow]")
                    progress.update(progress_task, advance=1)

            rprint("Copying legacy mesh assets...")
            self._copy_assets(source_dir=mesh_build_path, target_dir=f"{self.config.output_path}/meshes", filetype="mesh")

        legacy_audio_dir = f"{self.config.project_path}/src/legacy/audio"
        if Path(legacy_audio_dir).is_dir():
            rprint("Copying legacy audio assets...")
            self._copy_assets(source_dir=legacy_audio_dir, target_dir=f"{self.config.output_path}/audio", filetype="ogg")

        legacy_definitions_dir = f"{self.config.project_path}/src/legacy/definitions"
        if Path(legacy_definitions_dir).is_dir():
            rprint("Copying legacy definition files...")
            self._copy_assets(source_dir=legacy_definitions_dir, target_dir=f"{self.config.output_path}/data/definitions", filetype="xml")

    async def _compile_component_mesh(self, filename: str, component_build_path: str) -> Optional[int]:
        cmd = MESH_COMPILER_CMD + [filename] + ["-o", component_build_path]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=set_env(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode

    async def _compile_component_bin(self, definition_file: str, assets: list[str], component_build_path: str) -> Optional[int]:
        cmd = MOD_COMPILER_CMD + [definition_file] + [*assets]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=set_env(),
            cwd=component_build_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode

    def _get_component_definition_file_path(self, component_dir: str) -> str | None:
        files = os.listdir(f"src/{component_dir}")

        xml_files = [x for x in files if x.endswith(".xml")]
        if len(xml_files) > 1:
            rprint(f"[red]Error:[/red] Skipping component; found more than one XML file in src/{component_dir}.")
            return None
        elif len(xml_files) == 0:
            rprint(f"[red]Error:[/red] Skipping component; no XML file found in src/{component_dir}.")
            return None

        return xml_files[0]

    def _get_component_lua_file_path(self, definition_file: str, component_dir: str) -> str | None:
        files = os.listdir(f"src/{component_dir}")

        lua_files = [x for x in files if x.endswith(".lua")]
        if not lua_files:
            return None

        filename = definition_file.replace(".xml", ".lua")
        if filename in lua_files:
            return filename
        else:
            return None

    async def _compile_component_lua(self, filename: str, component_dir: str, component_build_path: str):
        cmd = ["darklua", "process"] + [f"src/{component_dir}/{filename}"] + [f"{component_build_path}/{filename}"]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode

    def _copy_component_assets(self, definition_file: str, component_dir: str, component_build_path: str) -> None:
        files = os.listdir(f"src/{component_dir}")

        ogg_files = sorted([x for x in files if x.endswith(".ogg")])

        for filename in [definition_file] + ogg_files:
            shutil.copy(f"src/{component_dir}/{filename}", f"{component_build_path}/{filename}")

    async def _build_component(self, definition_file: str, component_dir: str, component_build_path: str) -> None:
        self._copy_component_assets(definition_file, component_dir, component_build_path)

        assets = os.listdir(component_build_path)
        await self._compile_component_bin(definition_file, assets, component_build_path)

        bin_file = definition_file.replace(".xml", ".bin")
        bin_path = f"{component_build_path}/{bin_file}"
        if not Path(bin_path).is_file():
            rprint(f"[red]Error:[/red] Component bin compilation failed for {component_dir}.")

        shutil.copy(bin_path, f"{self.config.output_path}/data/components/{bin_file}")

    async def _build_components(self):
        rprint("Compiling component binaries...")

        component_dirs = [x for x in os.listdir(f"{self.config.project_path}/src") if x not in ["legacy", "lib"]]

        mesh_tasks = []
        lua_tasks = []
        bin_tasks = []

        for component_dir in component_dirs:
            definition_file = self._get_component_definition_file_path(component_dir)

            component_build_path = f"/tmp/sw-mod-builder/{self.config.build_name}/build/components/{component_dir}"
            Path(component_build_path).mkdir(parents=True, exist_ok=True)

            dae_files = [x for x in os.listdir(f"src/{component_dir}") if x.endswith(".dae")]
            for filename in dae_files:
                mesh_task = self._compile_component_mesh(f"src/{component_dir}/{filename}", component_build_path)
                mesh_tasks.append(mesh_task)

            lua_file = self._get_component_lua_file_path(definition_file, component_dir)
            if lua_file:
                lua_task = self._compile_component_lua(lua_file, component_dir, component_build_path)
                lua_tasks.append(lua_task)

            bin_task = self._build_component(definition_file, component_dir, component_build_path)
            bin_tasks.append(bin_task)

        with Progress(transient=True) as progress:
            mesh_progress_task = progress.add_task("Compiling component meshes...", total=len(mesh_tasks))
            async for task in asyncio.as_completed(mesh_tasks):
                progress.update(mesh_progress_task, advance=1)

        with Progress(transient=True) as progress:
            lua_progress_task = progress.add_task("Compiling component lua...", total=len(lua_tasks))
            async for task in asyncio.as_completed(lua_tasks):
                progress.update(lua_progress_task, advance=1)

        with Progress(transient=True) as progress:
            bin_progress_task = progress.add_task("Compiling component binaries...", total=len(bin_tasks))
            async for task in asyncio.as_completed(bin_tasks):
                progress.update(bin_progress_task, advance=1)

    async def run(self):
        rprint(f"Building mod [bold blue]{self.config.build_name}[/bold blue]...")
        self._verify_paths()
        self._clear_build_cache()
        self._prepare_build_paths()

        await self._build_legacy()

        await self._build_components()

        shutil.copy(f"{self.config.project_path}/mod.xml", f"{self.config.output_path}/mod.xml")
        shutil.copy(f"{self.config.project_path}/mod.png", f"{self.config.output_path}/mod.png")

        self._clear_build_cache()
        rprint(f"Done! Output is saved to the [bold yellow]build/{self.config.build_name}[/bold yellow] directory.")


class ValidateDirectoryAndContents(argparse.Action):
    """Verify that project dir exists and contains required files"""
    def __call__(self, parser, namespace, values, option_string=None):
        path = Path(values)
        if (values == '') or not (path.exists() and path.is_dir()):
            print("Provided path:", values)
            raise argparse.ArgumentError(self, 'Not a valid directory path.')
        # Should also validate that all required contents are present here
        setattr(namespace, self.dest, values)


def parse_args(argv: List[str]) -> argparse.Namespace:
    """                                                                                                      
    Parse argv object for CLI arguments.                                                                     
    """                                                                                                      
                                                                                                             
    desc = 'Builds a SW mod from a directory'
    epi = f'Example: \n\t{sys.argv[0]} <project dir>'
                                                                                                             
    parser = argparse.ArgumentParser(description=desc, epilog=epi)
    parser.add_argument(
            "project_dir",
            type=str,
            action=ValidateDirectoryAndContents,
            help='File containing mesh and mod definitions',
    )
                                                                                                             
    args = parser.parse_args(argv)                                                                           
                                                                                                             
    return args


def build(args: argparse.Namespace) -> int:
    project_dir: str = args.project_dir
    config = _load_config(project_dir)

    builder = ModBuilder(config)
    asyncio.run(builder.run())
    
    return 0


if __name__ == '__main__':
    sys.exit(build(parse_args(sys.argv[1:])))
