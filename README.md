# The Quadcopter Project Codebase

## Structure

- `archive/`: Deprecated code and previous results that were deemed ineffective,
  invalid or improperly recorded.
- `arduino/`: Code for each Arduino.
- `bf-conf/`: Modified betaflight-configurator source to enable control and
  telemetry with Python.
- `doc/`: Papers related to the physics of the project.
- `src/`: Source code for all python programs.
- `raw/`: All the raw data, in the form of json dumps of the `Data` class.

Within `src`, we have `bf.py` which contains a class that communicates with
betaflight-configurator. We also have `live.py` and `rec.py` for actually
conducting experiments. They rely on `utils.py` to work, which contains
`Arduino`, `Writer`, `Plotter` and `Recorder` classes.

## Setup

First, clone the repo along with submodules: `git clone --recurse-submodules
--remote-submodules $URL`.  At this stage, the submodules could potentially have
a detached HEAD (e.g. you forgot `--remote-submodules`, or submodule has not
been bumped in main).  To resolve this one needs to run `git checkout main` in
the submodule directories before making any commits in them.  If you have
already cloned the repo, then try `git submodule update --init`, then again
checkout main.

In order to use this project, one likely needs to prepare a python `venv` (for
python dependencies): The packages sourced in this project can be found in
`requirements.txt`. 

Use `nvm` to get the correct version of `npm` for `betaflight-configurator`. The
configurator will also likely need to be recompiled: Follow README instructions
in `bf-conf/`.

## Use

For usage of the code, the user is referred to the `README` files in the
subdirectories.

Python code is divided into libraries (`src/lib`) and experimental /
postprocessing parts (`src`). Most of the functions have been annotated with
input/output and their usage, and a brief introduction to the libraries can be
found in `src/lib/README.md`.

## Development

### Branching model

Generally speaking, the main/dev branching is obeyed. `dev` code only goes into
`main` when it's tested to be largely working. New minor work is largely just
being carried out on `main`.

## Ideas for further work

There are a few tasks that we did not have time to perform along the way. Some
notable examples are listed below.

- For a 9-axes load cell setup capable of resolving components, it is very
  difficult to make the wires exactly orthogonal. However, we can seek to find a
  matrix that accounts for the contribution of each load cell to the three
  components x, y and z. This can be obtained with measuring a few known forces,
  and using `numpy.lstsq`.
