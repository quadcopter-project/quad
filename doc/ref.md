# audio-fft.py

Records audio input and performs FFT on it live, for use in the quadcopter project.

## TODO
My microphone seems to suffer a lot from pink noise, or it might be a bug I've written: more testing required.

## NOTES
PyAudio doesn't have the greatest documentation, really.
First initialise the pyaudio stream, then discard first three seconds, during which my mic can do funny things.
Then we can store the data; Note pyaudio returns byte objects, which are converted to numpy arrays with np.frombuffer(). From then on it's standard data processing.

## SCIENTIFIC REFERENCES
BPF and Shaft frequencies domiannt up to ~6kHz https://arc.aiaa.org/doi/10.2514/6.2016-2873

## CODING REFERENCES
Basics of PyAudio https://realpython.com/playing-and-recording-sound-python/
PyAudio -> Numpy https://stackoverflow.com/questions/24974032/reading-realtime-audio-data-into-numpy-array
Update matplotlib in loop, no blocking: https://stackoverflow.com/questions/56178261/real-time-fft-plotting-in-python-matplotlib
numpy fft: https://numpy.org/doc/stable/reference/generated/numpy.fft.fft.html#numpy.fft.fft
numpy fftfreq: https://numpy.org/doc/stable/reference/generated/numpy.fft.fftfreq.html#numpy.fft.fftfreq
scipy filtering: https://scribe.rip/analytics-vidhya/how-to-filter-noise-with-a-low-pass-filter-python-885223e5e9b7
Animating multiple lines: https://libreddit.oxymagnesium.com/r/learnpython/comments/gg2goc/how_do_i_animate_multiple_lines_in_a_matplotlib/
Finding peaks with find_peaks: https://stackoverflow.com/questions/1713335/peak-finding-algorithm-for-python-scipy


