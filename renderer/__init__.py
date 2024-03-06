
import sys
import os.path
abspath = os.path.abspath(os.path.dirname(__file__))
# __package__ = ''

if abspath not in sys.path:
    print(abspath)
    sys.path.insert(0, abspath)


# # print(' -- __init__: importing renderer')
# # print(abspath)
# # print(os.path)
