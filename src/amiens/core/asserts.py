#!/usr/bin/python3

# Copyright 2015 Nathan Ross
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import os
from os import path
import amiens.core.util

def that(a, b, trace_distance=0):
    #using this keyword typically results in breaking
    # linebreak conventions.
    if (not a):
        amiens.core.util.Log.fatal(b, trace_distance+1)

def dne(goal, l, trace_distance=0):
    that(not (os.access(l, 0)),
         goal+' but a file already exists there', trace_distance+1)

def exists(goal, l, trace_distance=0):
    that(os.access(l, 0),
         goal+' but no such file exists', trace_distance+1)

def canwrite(goal, l, trace_distance=0):
    that(os.access(l, os.W_OK),
         goal+' but dont have write permissions', trace_distance+1)

def canread(goal, l, trace_distance=0):
    that(os.access(l, os.R_OK),
         goal+' but dont have read permissions', trace_distance+1)

def isdir(goal, l, trace_distance=0):
    that(path.isdir(l),
         goal+' but its not a directory', trace_distance+1)

def ispath(goal, l, trace_distance=0):
    that(path.exists(l),
         goal+' but its not a directory', trace_distance+1)

