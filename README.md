# amiens

## About

A library and command line tool for advanced (currently audio-only) media discovery via the internet archive. The internet archive is the world's largest collection of audio media. This library allows for:

 * search functions that use derivable data not available on archive.org (e.g. max or minimum total length of an item, audio bitrate (kbps) of an item). 

 * search functions that, for performance reasons, would be prohibitively expensive on a public-facing server that searched all of the archive's content. (e.g. instead of only searching isolated terms (exact matches), allow searches for words that contain or match particular terms; this means the search by necessity no longer can be const time (via const-time hash tables) for N archive items, instead being above const but sub-linear. - For a single user using a laptop processor, this is easily managable; on a public facing server you could get back to const most of the time by indexing the most popular 'match anywhere' terms and for ideographic alphabets indexing which items have the starting character, but there would be a long tail that would really slam the servers. Iterating over 50+ MB (tags and time metadata removed etc.) is just not cheap.

Operates over an expandable (and controllable) subset of internet archive items, under the premise that for several use cases, having this advanced search functionality offers more utility than ensuring one is searching the entirety of archive.org

Distributed for free, and freely usable, modifiable and redistributable under the Apache2 License. See the LICENSE file for important details.

Using this currently requires comfort with the command line and comfort with editing a list in a code file. Future directions for development may include a toy web-facing frontend to allow easy use of a limited subset of these search additions (e.g. total length, bitrate, file formats) in addition to a basic term search.

## Usage
```
amiens <command> <options>

  --- create ---------------
                create an amiens internet archive media catalogue.

  --- addidents ---------------
                add in identifiers

  --- learn ---------------
                fetch file data and metadata for different idents.

  --- metadata ---------------
                print metadata for an item to a text file to STDOUT

  --- review ---------------
                set the review info for an item

  --- download ---------------
                download or upgrade quality of an item. if the item exists already in the output directory, adds the files if none exist, or (atomically) upgrades the quality of each file if the files are of lower size.

  --- find ---------------
                search for items matching a metadata query,and add results to a folder of download stubs
```

## back-end dependencies

 * sqlite3
 * python3
 * python-sqlite
 * python3-defusedxml
 * p7zip
 * unzip
 * unrar-free
 * sox
 * libsox-fmt-mp3
 * libav-tools
 * flac
 * shntool
 * vorbis-tools