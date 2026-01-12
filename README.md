# Macroverse

[![Build Status](https://github.com/davidbrochart/macroverse/workflows/test/badge.svg)](https://github.com/davidbrochart/macroverse/actions)

[Jupyverse](https://github.com/jupyter-server/jupyverse) environment deployment.

## Installation

Install [micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html),
create an environment an install `macroverse` and `nginx`:

```bash
micromamba create -n macroverse
micromamba activate macroverse
micromamba install nginx pip
pip install macroverse
```

## Usage

### Process containers

In this configuration, Jupyter servers run in processes on the same machine.

Enter in the terminal:

```bash
macroverse --open-browser
```

This should open a browser window with a list of environments.
Click on `New environment` and enter an `Environment YAML`.
Click `Submit` and wait until the environment is created.
Click on `New server` and then on `Add environment(s)`, and enter the name of the environment you just created.
Then click on the link of the server. This should open JupyterLab in a new tab with the enabled environments.

### Docker containers

You must have Docker installed. In this configuration, Jupyter servers run in Docker containers.

Enter in the terminal:

```bash
macroverse --open-browser --container docker
```

The UX is the same as for process containers.
