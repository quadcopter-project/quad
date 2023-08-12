# this is so that relative path imports (imports used in lib files) can always work.
import os, sys
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
