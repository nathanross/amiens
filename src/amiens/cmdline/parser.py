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

from amiens import download, find, idents, createcatalogue, review, printmetadata, learn
from amiens.cmdline.transforms import Transforms
from amiens.core.util import Log, Bcolors

import argparse
import traceback

class _Command:
    def __init__(self, name, description, arguments, callback):
        self.name = name
        self.description = description
        self.arguments = arguments
        self.callback = callback

class _Arg:
    def __init__(self, ext, short, nargs, type, default, help,
                 transform=Transforms.dummy, required=False):
        self.ext = ext
        self.short = short
        self.nargs = nargs
        self.type = type
        self.default = default
        self.help = help
        self.transform = transform
        self.required = required

def _printUsage(commands):
    usage_instr = ['amiens <command> <options>']
    descript_spacer_length=14
    descript_spacer = ''.join([' ' for x in range(0,
                                                  descript_spacer_length)])
    for command in commands:
        commandtext='  --- '+command.name+ ' ---------------'
        usage_instr.extend(['', commandtext,
                            descript_spacer+command.description])
    print('usage:')
    print('\n'.join(usage_instr))
        
def parse(args_orig):
    #important distinction:
    # nargs=1 produces a list of 1 item
    #     if the option is used an arg must be provided, else err.
    # nargs='default' produces  the item itself.
    #     if the option is used an arg must be provided, else err.
    # nargs='?' produces the item itself.
    #     if the option is used without arg, the value is set to None.
    args = {
        'catalogue_path' : _Arg(ext='catalogue_path', short='-c',
                                nargs='default',
                                type=str, default="~/.amiens",
                                help=('path to database to use'),
                                transform=Transforms.useCatalogue),
        'media_type': _Arg(ext='media_type', short='-t',
                          nargs='default',
                          type=str, default="audio",
                          help=('restrict idents retrieved to'
                                'audio or video'),
                          transform=Transforms.mediaType),
        'data_src' : _Arg(ext='data_src', short='-s',
                          nargs='?',
                          type=str, default=None,
                          help=('if provided, instead of getting info from web'
                                'gets info from this db'),
                          transform=Transforms.data_src),
        'item' : _Arg(ext='item', short='-i',
                      nargs='default',
                      type=str, default="",
                      help=('item. currently only support passing'
                            'a directory or stubfile'),
                      transform=Transforms.item),
        'outdir' : _Arg(ext='outdir', short="-o",
                        nargs='default',
                        type=str, default='',
                        help='output directory',
                        transform=Transforms.outdir,
                        required=True),
        'scratchdir' : _Arg(ext='scratchdir', short="-x",
                        nargs='default',
                        type=str, default='/tmp/amiens_scratch',
                        help='output directory',
                        transform=Transforms.outdir),
        'quality' : _Arg(ext='quality', short="-q", 
                         nargs='default',
                         type=int, default=1,
                         help=('quality: 1 is (audio) 128kbps or below.'
                               '2 is (audio) 256kbps or below,'
                               '3 is highest available,'
                               '4 is everything.'),
                         transform=Transforms.quality),
        'filter_fq' : _Arg(ext='filter_fq', short="-f",
                     nargs='default',
                     type=str, default="qlib/fq.dummy.py3", 
                     help=('filequery which is used to filter find'
                           'and downloads which have non-matching'
                           'length, bitrate, size, etc.'),
                     transform=Transforms.mqs_fqs
                ),
    }
    commands = [
        _Command(
            name = 'create',
            description = 'create an amiens internet archive media catalogue.',
            arguments = [
                _Arg(ext='new_catalogue_path', short='-d',
                     nargs='default',
                     type=str, default="~/.amiens",
                     help=('path to catalogue to use'),
                     transform=Transforms.posix_generic)
            ],
            callback = createcatalogue.CreateCatalogue.cmd
        ),
        _Command(
            name = 'addidents',
            description = 'add in identifiers',
            arguments = [
                args['catalogue_path'],
                _Arg(ext='is_new_db', short='-n',
                     nargs='default',
                     type=int, default=0,
                     help=('dont check if theres already rows with any'
                           'of these idents before attempting to add'
                           'default false is safe no matter what.'
                           'But if you have never added idents'
                           'of this media type, this will be a much faster'
                           'option'),
                        transform=Transforms.boolean
                    ),
                args['media_type'],
                args['data_src'],          
            ],
            callback = idents.AddIdents.cmd
        ),
        _Command(
            name='learn',
            description='fetch file data and metadata for different idents.',
            arguments = [
                args['catalogue_path'],
                _Arg(ext='wait', short="-w",
                     nargs='default',
                     type=int, default=5,
                     help='number of minutes to fetch for. default is 5'),                
                _Arg(ext='fetch_m_fq', short="-q",
                     nargs='default',
                     type=str, default="qlib/fq.dummy.py3", 
                     help=('filequery which, by returning false,'
                           'can filter out which metas to fetch'
                           'based on size or length'),
                     transform=Transforms.mqs_fqs
                ),
                _Arg(ext='keep_m_mqs', short="-m",
                     nargs='+',
                     type=str, default="qlib/mq.dummy.py3", 
                     help=('metaquery which, by returning false, can'
                           'filter out which metas to keep based on'
                           'meta content.'),
                     transform=Transforms.mqs_fqs
                ),
                args['media_type'],
                args['data_src']
            ],
            callback = learn.Learn.cmd
        ),
        _Command(
            name = 'metadata',
            description = 'print metadata for an item to a text file to STDOUT',
            arguments = [
                args['catalogue_path'],
                args['item']
            ],
            callback = printmetadata.PrintMetadata.cmd
        ),
        _Command(
            name = 'review',
            description='set the review info for an item',
            arguments = [
                args['catalogue_path'],
                args['item'],
                _Arg(ext='comment', short='-c',
                     nargs='?', type=str, default=None,
                     help="get or set text comment for item"),
                _Arg(ext='rating', short='-r',
                     nargs='?', type=str, default=None,
                     help=('rate from 1-5'),
                     transform=Transforms.rating),
            ],
            callback = review.Review.cmd
        ),
        _Command(
            name = 'download',
            description=('download or upgrade quality of an item.'
                         ' if the item exists already in the output'
                         ' directory, adds the files if none exist,'
                         ' or (atomically) upgrades the quality of'
                         ' each file if the files are of lower size.'),
            arguments = [
                args['item'],
                args['scratchdir'],
                args['outdir'],
                args['quality'],
                args['filter_fq']
            ],
            callback = download.Download.cmd
        ),
        _Command(
            name = 'find',
            description=('search for items matching a metadata query,'
                         'and add results to a folder of download stubs'),
            arguments = [
                args['catalogue_path'],
                args['scratchdir'],
                args['outdir'],
                args['quality'],
                _Arg(ext='download', short='-d',
                     nargs='default',
                     type=int, default=0,
                     help=('download items automatically instead of'
                           'just downloading stubs'),
                     transform=Transforms.boolean
                 ),
                _Arg(ext='test_limit', short='-t',
                     nargs='default',
                     type=int, default=100000,
                     help="number of metadata items to search across."),
                _Arg(ext='result_limit', short='-l',
                     nargs='default',
                     type=int, default=1000,
                     help="number of results to return."),
                args['filter_fq'],
                _Arg(ext='mqs', short='-m',
                     nargs='+',
                     type=str, default='',
                     help="files to use as metadata filters",
                     transform=Transforms.mqs_fqs),
            ],
            callback = find.Find.cmd
        )
    ]

    if len(args_orig) == 0:
        _printUsage(commands)
        return False
    command_rcvd = args_orig[0]
    args_rcvd = args_orig[1:]
    Parser = argparse.ArgumentParser

    for command in commands:
        if args_orig[0] == command.name:
            Log.debug('command is: ' + command.name)
            parser = Parser(description=(command.name+' : '+command.description))
            for arg in command.arguments:
                Log.debug(', '.join([
                    'parser.add_argument ##'
                    'ext:'+arg.ext,
                    'short:'+arg.short,
                    'nargs:'+arg.nargs,
                    'type:'+repr(arg.type),
                    'default:'+repr(arg.default),
                    'help:'+repr(arg.help)]))
                if arg.nargs =='default':
                    # shame that argparse doesn't allow passing
                    # the value for 'default' for nargs.
                    parser.add_argument('--'+arg.ext,
                                        arg.short,
                                        type=arg.type,
                                        default=arg.default,
                                        help=arg.help,
                                        required=arg.required)
                else:
                    parser.add_argument('--'+arg.ext,
                                        arg.short,
                                        nargs=arg.nargs,
                                        type=arg.type,
                                        default=arg.default,
                                        help=arg.help,
                                        required=arg.required)
            raw_args=vars(parser.parse_args(args_rcvd))
            transformed_args={}
            Log.data('parsed_subcmd_args(raw):'+repr(raw_args))
            for arg in command.arguments:
                if arg.ext in raw_args:
                    transformed_args[arg.ext] = arg.transform(raw_args[arg.ext])
            Log.data('parsed_subcmd_args(transformed):'+repr(transformed_args))
            try:
                command.callback(transformed_args)
            except KeyError:
                print(Bcolors.L_RED.value)
                traceback.print_exc()
                print(Bcolors.NORMAL.value)
            return True
        
    _printUsage(commands)
    return False

