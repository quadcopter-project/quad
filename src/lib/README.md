# Libraries

## Introduction

The libraries can be divided into three sets by function: 

- Device interfaces (`drone`, `utils.Recorder`, `ard`)
- Data storage (`utils.Frame`, `utils.Data`) and
- Data processing (`plotter`, `processor`).

Device interfaces contains device controls where applicable (RPM, height of
drone, etc.), and provides access to device readings. These readings are then
collected and passed into `utils.Data`. A `Data` instance then allows data
storage to (`Data.dump()`), and recovery from (`Data.load()`) disk.

`Data` instances also enables access to processing tools such as the live
plotter (`plotter.Plotter`, through `Plotter.plot()`) which takes a single data
instance as input. Most functions in `processor` will need to take in a list of
data instances, exported files of which can be loaded with relative ease with
`proessor.get_data_list()`

Some of the classes contain annotations of public/private methods. Unless bugs
are encountered, the public methods are sufficient and the private ones should
not concern the user too much.

Running some of the libraries as main will cause them to perform tests; These
have not been run for long and so could be broken.

The user is also recommended to browse through `src/live-bf-2.py` for an example
of the libraries at work.

## Arduino (`ard.Arduino`, `ard.ArdManager`)

In principle, the only class that needs to be invoked is `ArdManager`, a wrapper
for the `Arduino` class that scans and connects to Arduinos on instantiation.
Under the hood, each `Arduino` instance connects to an individual Arduino,
and continuously fetches the most recent data with a background thread.

The only recommended method for obtaining Arduino reading is `get_reading`,
while for controls, one can call `level`, `set_height`, `move` and `tare` in
`ArdManager`. 

With a `__getattr__` trick, on invoking any method not contained in `ArdManager`
but in `Arduino`, `ArdManager` merely calls that method on every `Arduino`.  A
control signal that only applies to some of the Arduinos is allowed, as the
other Arduinos will simply ignore the invalid call.

The individual `Arduino` instances can be accessed by their device ID, like a
regular index (`ardman[dev_id]`). The individual sensors and motors can also be
remapped and relabelled in `ArdManager` with the `*_mapping` functions, and the
mapping saved / loaded with `dump` and `load` functions, however this is less
tested.

## Betaflight (`drone.Drone`)

The `Drone` class is in charge of the betaflight drone, or more precisely, the
`betaflight-configurator` which it talks to and controls via a websocket on a
background thread.

Provided that the project structure doesn't change significantly, the
configurator can be auto-launched on instantiation.

The key control methods are `Drone.set_arming`, `Drone.set_rpm_worker_on`
(required before RPM control can be turned on), `Drone.set_throttle` and
`Drone.set_rpm`. D-Shot RPM data is obtained with `Drone.get_rpm`. For an
example workflow, see the test functions at the end of `drone.py`.

## ViveTracker (`viveTracker.ViveTracker`, `viveTracker.TrackerSpace`)

The `ViveTracker` class uses API provided by `triad_openvr` to create an object storing the properties of a vive Tracking device. `TrackerSpace` scans all connected trackers and create corresponding `ViveTracker` objects upon initialization. 

In the current experiment setup, two trackers are used and one of the tracker is placed on the ground as reference for zero height. Running `TrackerSpace.calibrateGround()` will update offset parameter for all `ViveTracker` object, ensuring the lowest tracker have a combined height of zero. 

As the trackers relies on both inertial estimation and laser sheet tracking, huge vibration from high rpm will cause the software to lose tracking. Once tracking is lost, the `ViveTracker` object returns height of its last recorded height. At the same time, a `ViveTracker.recent_reconnect` flag is changed to True. This can be used and reset for repeating measurements. 

## Audio Server & Client (`AudioServer.AudioServer`, `AudioClient`)

An implementation of continuous audio recording method that runs in parallel to all other script. Running `AudioServer` in main on another thread will initiate the server. The server constantly listen to localhost port 9000 and wait for commands. `AudioClient` is able to configure command and send to corresponding port. The program is not asynchronous and cannot respond once recording is in progress, thus the command contains the duration of the recording. Once the recording is finished, a .wav file is stored with file name specified in the initial command given.

## Audio (`utils.Recorder`)

The `Recorder` class is really just a wrapper around PyAudio. It comes with a
set of "sensible defaults" for PyAudio which may well fail for a different
device. These can be changed in the code, or overloaded by specifying new values
in the `**kwargs` of the initialiser. 

If you are not running Linux and / or not using PipeWire as your audio server,
you will most certainly need to supply a new `device_name` as well. To check
what audio inputs are available on your device, run `Recorder.get_outputs`.

Recording itself is as simple as `Recorder.record`; When finished, it is
advisable to close the PyAudio interface with `Recorder.close`.

## Data (`utils.Frame`, `utils.Data`)

We must first cover `utils.Frame`. It represents readings from all sources at a
given point in time, and has one or two helper functions built in.

The `Data` class is essentially just a wrapper for a list of `utils.Frame`, with
extra metadata and built-in helper functions to help add or extract data. In
fact, `Data` can be used simply as a list, using indices to access frames. The
most useful is the `add` method, which takes a bunch of inputs (essentially,
everything that a `Frame` can store), and create a new frame and insert it into
its list of frames. `__getattr__` implementation means that one can obtain a
list of any variable in `Frame` by just calling `Data.get_variable_name`,
substituting the `variable_name`. In fact, it will also take advantage of
`get_*` functions in `Frame`.

`Data` save/load is managed by `Data.dump` and `Data.load`. Direct
initialization with path name to saved file is not supported.

Both `Data` and `Frame` are `dataclass`es, meaning that, predefined initialisers
are present, equalities compare all instance members, etc.

## Live plotting (`plotter.Plotter`)

`Plotter` leverages the `ion` option in `matplotlib` to achieve real-time
plotting. The flexibility of plotting layout and variety of supported plots come
at the cost of a simple initialiser. The user is required to supply the rows and
columns of the grid of plots, and the role of each. The latter is specified by a
dictionary `graph_types`, mapping a coordinate of (row, column) to a
`graph_type` in the `SUPPORTED` list.

Once these information is supplied, `Plotter` exposes `Plotter.plot`, which
takes a `Data` object and processes it, plotting the different graphs according
to the specified mapping in `graph_types`.

It is relatively easy to extend `Plotter` capabilities; Please refer to comments
at the top of `plotter.py` for how this may be done. 

## Data processing (`processor`)

Because most functions in `processor` does something completely different, the
only suggestion is that the user should try to find the function they need by
the function names, and refer to comments when necessary. The old, "legacy"
snaptain analysis code is separated from the betaflight code by a comment block.

A few commonly used, "generic" processing functions are found at the beginning
of the file. Most notably, because a lot of processing functions require a list
of data objects, or a `data_list`, one may find the function `get_data_list`
very useful. Two other important functions are `remove_outliers` and
`errorbar_plot`.
