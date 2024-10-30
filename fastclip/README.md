# Fastclip

You're probably asking yourself why there is a small C++ project
buried in a python project ? Better Performance for processing large
data files. This utility is to improve the data splitting of the large
files. While it is possible to do this using command line tools, you
have to use multiple tools to do both tag filtering and data
clipping. And each step requires the proper command line parameters to
produce the file in the right format for conflation.

Since the goal of this project is to have a data flow anyone can use, 
this tool combines all the steps required. And it's an order of
magnitude that the python version.

