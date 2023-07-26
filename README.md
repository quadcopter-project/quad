# The Quadcopter Project Codebase

## Structure

`archive`: stocks unneeded code / other stuff.
`arduino`: stores the code running on the arduino (loadcell, motor) 
`bf-conf`: betaflight-configurator (modified) source.
`doc`: some relevant documents.
`env`: python virtualenv.
`results`: recorded data, in spreadsheets.
`src`: source code for all python programs.

Within `src`, we have `bf.py` which contains a class that communicates with betaflight-configurator. We also have `live.py` and `rec.py` for actually conducting experiments. They rely on `utils.py` to work, which contains `Arduino`, `Writer`, `Plotter` and `Recorder` classes.

## Use
To setup `bf-conf`, read its README. As for just the environments, do:

```bash
source env/bin/activate
nvm use
```
If there are any missing dependencies, merely do `pip install` until you get no `import` errors, because I am too lazy to get a requirement.txt.
