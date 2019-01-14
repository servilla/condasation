#!/usr/bin/env python
# -*- coding: utf-8 -*-

""":Mod: env

:Synopsis:

:Author:
    servilla

:Created:
    1/13/19
"""
import json
import pathlib

from bs4 import BeautifulSoup
import click
import daiquiri
from lxml import etree
import yaml
import requests

logger = daiquiri.getLogger('env: ' + __name__)


def build_conda_cache(base_url: str, channel: str):
    cache = dict()
    url = f'{base_url}/{channel}/repodata2.json'
    r = requests.get(url)
    r.raise_for_status()
    repodata2 = json.loads(r.text)
    packages = repodata2['packages']
    for package in packages:
        name = package['name']
        version = package['version']
        if name in cache:
            if version not in cache[name]:
                cache[name].append(version)
        else:
            cache[name] = [version]
    return cache


def build_env_cache(env: str):
    cache = dict()
    with open(env, 'r') as f:
        env_yml = yaml.load(f)
    dependencies = env_yml['dependencies']
    for dependency in dependencies:
        if isinstance(dependency, str):
            name, version = dependency.split('=')
            cache[name] = version
    return cache


def fix_conda_env(env: str, missing: dict):
    with open(env, 'r') as f:
        env_yml = yaml.load(f)
    dependencies = env_yml['dependencies']
    for package in missing:
        version = missing[package]
        pv = f'{package}={version}'
        if pv in dependencies:
            dependencies.remove(pv)
    return env_yml


def list_channels(base_url: str):
    url = f'{base_url}/'
    r = requests.get(url)
    r.raise_for_status()
    html = etree.fromstring(r.text.replace('&nbsp;', '').encode('utf-8'))
    _ = html.findall('.//body/a')
    for a in _:
        click.echo(a.text)


channels_help = 'Comma separerate list of Anaconda channels to evaluate (default: linux-64,win-64)'
env_help = 'Evnironment file to inspect (default: environment.yml)'
fix_help = 'Output a corrected version of the Conda export file'
list_help = 'List available Anaconda channels then exit ignoring other commands'

@click.command()
@click.option('-c', '--channels', default='linux-64,win-64', help=channels_help)
@click.option('-e', '--env', default='environment.yml', help=env_help)
@click.option('-f', '--fix', is_flag=True, help=fix_help)
@click.option('-l', '--list', is_flag=True, help=list_help)
def env(channels: str, env: str, fix: bool, list: bool):
    """Inspect and report on a Conda environment based on the environment.yml
       for packages that are not available in all of the standard OS
       distributions - this generally means the package is a specific upstream
       OS package that can be removed from the environment.yml file.
    """

    base_url = 'https://repo.anaconda.com/pkgs/main'

    if list:
        list_channels(base_url=base_url)
        return 0

    conda_env_cache = build_env_cache(env)

    channel_cache = dict()
    channels = channels.strip().split(',')
    for channel in channels:
        channel_cache[channel] = build_conda_cache(base_url=base_url,
                                                   channel=channel)
    missing = dict()
    for package in conda_env_cache:
        in_all = True
        version = conda_env_cache[package]
        for channel in channels:
            _ = channel_cache[channel]
            if package not in _ or version not in _[package]:
                    in_all = False
                    break
        if not in_all:
            missing[package] = version

    if fix:
        fixed_yml = fix_conda_env(env, missing)
        click.echo(yaml.dump(fixed_yml, default_flow_style=False))
    else:
        for name in missing:
            click.echo(f'{name}={missing[name]}')

    return 0


if __name__ == "__main__":
    env()
