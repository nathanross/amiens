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

import amiens.core.asserts
from enum import Enum, IntEnum
import os
from os import path
import inspect
import sys
import json



def debug_open(goal, l, opentype):
    try:
        return open(l, opentype)
    except IOError as e:
        Log.fatal(goal)
    except:
        Log.fatal(goal)

def full_read(goal, l):
    f=debug_open(goal, l, 'r')
    d=f.read()
    f.close()
    return d

def full_write(goal, l, d):
    f=debug_open(goal, l, 'w')
    f.write(d)
    f.flush()
    f.close()

def json_read(goal, l):
    return json.loads(full_read(goal, l))

def json_write(goal, l, d):
    full_write(goal, l, json.dumps(d))


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i
                                                                                    
class LogSeverity(IntEnum):
    DATA_LOSS=0
    FATAL=1
    ERROR=2
    LIKELY_ERROR=3
    WARNING=4
    WRITES=5
    OUTLINE=6
    DATA=7
    DEBUG=8
    FORCE=9

class Bcolors(Enum):
    NORMAL = '\033[0m'
    BLACK = '\033[0;30m'
    D_RED ='\033[0;31m'
    D_GREEN = '\033[0;32m'
    BROWN = '\033[0;33m'
    D_BLUE = '\033[0;34m'
    D_PURPLE = '\033[0;35m'
    D_CYAN ='\033[0;36m'
    D_GRAY ='\033[1;30m'
    L_GRAY ='\033[0;37m'
    L_RED ='\033[0;31m'
    L_GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    L_BLUE = '\033[1;34m'
    L_PURPLE = '\033[1;35m'
    L_CYAN ='\033[1;36m'
    WHITE = '\033[1;37m'
    U_RED ='\033[4;31m'

class Log(object):
    
    @staticmethod
    def logColor(level):
        if level == LogSeverity.DATA_LOSS:
            return Bcolors.U_RED
        elif level == LogSeverity.FATAL:
            return Bcolors.L_RED
        elif level <= LogSeverity.LIKELY_ERROR:
            return Bcolors.D_RED
        elif level == LogSeverity.WARNING:
            return Bcolors.YELLOW
        elif level == LogSeverity.DATA:
            return Bcolors.D_BLUE
        elif level == LogSeverity.DEBUG:
            return Bcolors.D_GREEN
        elif level == LogSeverity.FORCE:
            return Bcolors.L_CYAN
        return Bcolors.NORMAL
    
    
    @staticmethod
    def getTrace(level=1):
        #by default gets the file, funcname, line, of calling
        #function.
        stack_full=inspect.stack(level)
        tb_item= stack_full[-1]
        if len(stack_full) > level:
            tb_item= stack_full[level]
        return {
            'filename':tb_item[1],
            'line_num':tb_item[2],
            'func_name':tb_item[3]
        }

    @staticmethod
    def log(level, message, trace_distance=0):
        display_up_to=LogSeverity.LIKELY_ERROR
        if 'VERBOSE' in os.environ:
            display_up_to=int(os.environ['VERBOSE'])
        if level == LogSeverity.FORCE or level <= display_up_to:
            context_segment=''
            if level == LogSeverity.FORCE or \
               display_up_to >= LogSeverity.DATA:
                context=Log.getTrace(trace_distance+2)
                #rm .py
                pathstr=context['filename'][:-3]
                patharr=[path.basename(pathstr)]
                pathstr=path.dirname(pathstr)
                try:
                    while not os.access(pathstr + '/__init__.py',0):
                        patharr.insert(0, path.basename(pathstr))
                        pathstr=path.dirname(pathstr)
                except:
                    raise Exception('error! your package must have an'
                                    '__init__.py file at its root')
                pathstr='/'.join(patharr)
                context_segment=''.join([
                    pathstr,
                    ' @ ',
                    str(context['line_num']),
                    ' ',
                    context['func_name'],
                    '(..) '                    
                ])
            print(''.join([
                (Log.logColor(level)).value,
                context_segment,
                message,
                Bcolors.NORMAL.value
            ]))
        if level <= LogSeverity.FATAL:
            raise Exception(message)
    
    @staticmethod
    def data_loss(text, trace_distance=0):
        Log.log(LogSeverity.DATA_LOSS, text, trace_distance+1)
    
    @staticmethod        
    def fatal(text, trace_distance=0):
        Log.log(LogSeverity.FATAL, text, trace_distance+1)
    
    @staticmethod        
    def error(text, trace_distance=0):
        Log.log(LogSeverity.ERROR, text, trace_distance+1)
    
    @staticmethod        
    def likely_error(text, trace_distance=0):
        Log.log(LogSeverity.LIKELY_ERROR, text, trace_distance+1)
    
    @staticmethod
    def warning(text, trace_distance=0):
        Log.log(LogSeverity.WARNING, text, trace_distance+1)
    
    @staticmethod        
    def writes(text, trace_distance=0):
        Log.log(LogSeverity.WRITES, text, trace_distance+1)
    
    @staticmethod        
    def outline(text, trace_distance=0):
        Log.log(LogSeverity.OUTLINE, text, trace_distance+1)
    
    @staticmethod
    def data(text, trace_distance=0):
        Log.log(LogSeverity.DATA, text, trace_distance+1)
    
    @staticmethod
    def debug(text, trace_distance=0):
        Log.log(LogSeverity.DEBUG, text, trace_distance+1)
    
    @staticmethod        
    def force(text, trace_distance=0):
        Log.log(LogSeverity.FORCE, text, trace_distance+1)
