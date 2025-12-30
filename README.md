# Macroverse

[Jupyverse](https://github.com/jupyter-server/jupyverse) deployment.

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

In this configuration, Jupyter kernel servers run in processes on the same machine.

Enter in the terminal:

```bash
macroverse --open-browser
```

This should open a browser window with a list of environments.
Click on `New environment` and enter this `Environment YAML`:

```yaml
name: my-env
channels:
  - conda-forge
dependencies:
  - ipykernel
  - matplotlib
  - numpy
```

Click `Submit` and wait until the environment is created. Then click `Start server` next to your environment name.
This should change the environment name into a link. If you click on it, this should open JupyterLab in a new tab.

### Docker containers

You must have Docker installed. In this configuration, Jupyter kernel servers run in Docker containers.

Enter in the terminal:

```bash
macroverse --open-browser --container docker
```

The UX is the same as for process containers.
