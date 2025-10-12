# Audite

This repository is a bunch of scripts that help to organize a completely offline collection of music files. The scripts and their aims are explained below in subsections.

## Audite.py

This is the core script of repository. A collection of music files typically has the following structure:  
```
Base/
    /Artist, A.B./
             /1999 - Album 1/
                            /01. Song.flac
                            /...
                            /12. Outro.flac
                            /cover.jpg
                            /Cover (larger).jpg
                            /cuesheet-for-this-album.cue
             /2003 - Singles/...
    /Band, The C/...
    /...
    /Miscellaneous/
                  /1. Rogue.flac
                  /...
                  /9. Outcast.flac
                  /cover.jpg
                  /noname.cue
```

Audite can be applied either to an artist/band folder or to a single album (e.g. `Miscellaneous` above).

Audite is intended to:
* format FLAC and MP3 music file names and their metadata according to cuesheet CUE files
* format track titles and album titles, primarily to force smart capitalization of words
* update replay-gain information in FLAC and MP3 files to normalize loudness
* convert M4A music files into FLAC
* format cover images to be 1000px in height (original image is preserved) and engrave them into tracks
* rename album folders according to cuesheet metadata and flatten complex albums (e.g. Album/CD1/\*, Album/CD2/\* $\rightarrow$ Album/\*)
* reconstruct missing metadata in cuesheets guessing it from existing track metadata or explicitly user-given hints

Audite is not intended to:
* download anything from the Web (to avoid copyright issues)
* consult Web for missing metadata (to avoid further uncertainty)

Evidently, Audite cannot reconstruct completely missing or erroneous metadata. In these cases user might manually correct cuesheet files or pass some metadata to Audite directly.

When a misformatted and ugly looking collection of music tracks is supplied with a proper bunch of cuesheets, Audite can suggest and carry out changes that will make an inveterate perfectionist smile!

Unfortunately, during the initial development of `Audite.py` some entropy has leaked into the source code. In spite of being chaos exterminator, `Audite.py` has become somewhat messy itself.

See `--help` text and comments within `Audite.py` for further details on script usage and implemented formatting rules.

## Playlister.py

Once an offline audio library has been established and nicely formatted by Audite, one would take pleasure of listening to music tracks and sorting them into playlists. A playlist may be:
1. a folder with symbolic links pointing to favourite audiofiles
2. an M3U text file with paths to the same audiofiles

When the same playlist is represented by different means (perhaps, on different devices), it soon becomes desirable to synchronize them.

Playlister is intended to:
* read symbolic links from a directory, translate them into a listing and update an existing M3U list with them
* read an existing M3U list, construct symbolic links from its entries and append them into an existing folder
* optionally sort the M3U list
* report the counts of duplicates, broken links, etc.
* ask for user intervention in ambiguous cases
