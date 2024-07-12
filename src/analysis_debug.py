
from lib.utils import Data
from time import sleep
from lib import processor

import os
import statistics as st
import numpy as np
import matplotlib.pyplot as plt

from tkinter import Tk
from tkinter.filedialog import askopenfilename

path = './data/smallframe/10-07-2024-4-50cm-hr'
new_path = './data/smallframe/10-07-2024-4-50cm-hr-selected/'
processed_path = './processed_data/smallframe/5-100cm-total'
#print(processor.get_data_files(path))
#print(processor.get_data_files_newest(path))
data_files = processor.get_data_files_newest(path)
#print(data_files)
#processor.preview_data(data_files,new_path)
#processor.get_data_list_with_height_reassignment(data_files)
processor.process_and_dump_with_height_adj(new_path, processed_path)
