# Installation

## Create & Activate Virtual Environment

We recommend creating a virtual Python environment using venv:

```sh
python -m venv .venv
```

Activate the virtual environment:

```sh
# Mac / Linux
source .venv/bin/activate

# Windows CMD
.venv\Scripts\activate.bat

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

## Install ADK

Install the ADK package:

```sh
pip install google-adk
```

(Optional) Verify your installation:

```sh
pip show google-adk
```

You are now ready to create your first agent. See the Quickstart for next steps.

See the official docs for platform-specific notes. 