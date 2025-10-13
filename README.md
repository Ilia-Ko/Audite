# Audite Scripts

Present repository is a bunch of scripts that help to organize a local (or self-hosted) collection of music files. The scripts and their aims are described below in subsections.

The scripts have been developed and tested under [Arch Linux](https://archlinux.org) 6.17.1 environment and do have external dependencies as listed below for each script.

## Cuesplitter.sh

`Cuesplitter.sh` is an auxiliary script that may be helpful if an existing audio data is not separated into individual music tracks yet. If you already possess a collection of individual music tracks (single file $-$ single track), skip this subsection and consider `Audite.py` straight away.

Sometimes one begins with music library of the following **preliminary** structure:
```
Base/
    /Artist, A.B./
                 /1999 - Album 1/
                                /album-1.flac
                                /album-1.cue
                                /cover.jpg
                 /2001 - Album 2/
                                /album-2.flac
                                /album-2.cue
                                /folder.jpeg
                 ...
    ...
    /Miscellaneous/
                  /misc.flac
                  /misc.cue
                  /front.png

```
where audio files `album-1.flac`, `album-2.flac` and `misc.flac` contain several simply concatenated music tracks each. Corresponding cuesheet files define timecodes when every track begins and album/track metadata.

Some music players, especially standalone devices, do not feel themselves confident enough around such **preliminary** music library. Maintenance of typical playlists (see 2 types of playlists in subsection `Playlister.py`) becomes also quite problematic, unless music library is converted into a **normalized** structure (see subsection `Audite.py` below).

`Cuesplitter.sh` takes 1 argument (base directory) and is intended to:
1. find all available cuesheet files recursively starting from a given base directory (e.g. folder `Base` or folder `Artist, A.B.`)
2. for each cuesheet (e.g. `misc.cue`), find a corresponding audio file (`misc.flac`) and split it into multiple music tracks according to defined splitpoint timecodes. The tracks are named consistently with cuesheet as `XX. Track Title.flac`
3. annotate resulting music tracks with metadata from the cuesheet and embed cover image (if available) into each track
4. **rename** processed source audio files like `misc.flac` $\rightarrow$ `misc.flac0`. Later, user may manually verify that everything has been split properly and easily erase them with command:  
`find Base/ -type f -iname "*.flac0" -print -delete | tee deleted.log`

`Cuesplitter.sh` is not intended to:
* leave your music library in a 'perfectly' formatted/unified state
* complete missing metadata in cuesheets
* scale cover images properly
* download anything from the Web (to avoid copyright issues)

`Cuesplitter.sh` natively supports FLAC and MP3 audio files; M4A, APE and WV files are first converted into FLAC and then processed as usual.

Being an auxiliary script that only converts a **preliminary** music library into its **normalized** form, `Cuesplitter.sh` may still leave some misformatted metadata or misformatted track/album names. Furthermore, `Cuesplitter.sh` does not scale cover images properly (it is even better not to provide large cover images for `Cuesplitter.sh`). Therefore, a major formatting task is delegated to the core `Audite.py` script, described in the next subsection.

### Dependencies

The versions of packages listed below are sufficient but not strictly necessary to run this script. It may work with older versions as well.

* [FFmpeg](https://ffmpeg.org/) n8.0, providing `ffmpeg` utility
* [FLAC](https://xiph.org/flac/index.html) 1.5.0, providing `metaflac` utility
* [Mutagen](https://github.com/quodlibet/mutagen) 1.47.3, providing `mid3v2` utility
* [find](https://www.gnu.org/software/findutils/) 4.10.0, [grep](https://www.gnu.org/software/grep/) 3.12, [GNU awk](https://www.gnu.org/software/gawk/gawk.html) 5.3.2, [iconv](https://www.gnu.org/software/libiconv/) 2.42
* [bash](https://www.gnu.org/software/bash/bash.html) 5.3.3, providing `readarray`, `printf`, `head`, `tail`, `echo`, `pwd`, `cd`, `rm`, `mv`, `mkdir`
* [Python](https://www.python.org/) 3.13.7

## Audite.py

`Audite.py` is the core script of repository. It plays the major role in standard formatting and unification of self-hosted music collection.

A local/self-hosted collection of music files may have the following **normalized** structure:  
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
                 /2025 - Singles/...
    /Band, The C./...
    /...
    /Miscellaneous/
                  /1. Rogue.flac
                  /...
                  /9. Outcast.flac
                  /cover.jpg
                  /noname.cue
```

`Audite.py` can be applied either to an artist/band folder (see Scenario A in `--help` letter) or to a single album such as `Miscellaneous` (see Scenario B in `--help` letter).

`Audite.py` is intended to:
* format FLAC and MP3 music file names and their metadata according to cuesheet CUE files
* format track titles and album titles, primarily to force smart capitalization of words if required
* update replay-gain information in FLAC and MP3 files to normalize loudness
* convert M4A music files into FLAC if any
* scale cover images to be roughly square, 1000 px in height and 200-800 KiB in size (original larger image is preserved) and embed them directly into track files
* maintain not only presence, but also uniqueness of track metadata and cover image
* rename album folders according to cuesheet metadata and flatten complex albums (e.g. `Album/CD1/*`, `Album/CD2/*` $\rightarrow$ `Album/*`)
* reconstruct missing metadata in cuesheets (or whole cuesheets when absent) guessing it from existing track metadata or explicitly user-given hints

`Audite.py` is not intended to:
* download anything from the Web (to avoid copyright issues)
* consult Web for missing metadata (to avoid further uncertainty)

Evidently, `Audite.py` cannot reconstruct completely missing or erroneous metadata. In these cases user might manually correct cuesheet files or pass some metadata to `Audite.py` directly. When cuesheet is absent itself, `Audite.py` will try to generate it consulting track built-in metadata and user-given hints. Later, user may refer to external database (e.g. https://www.discogs.com) to complete manually the cuesheet draft generated by `Audite.py`. See also API documentation at https://www.discogs.com/developers/ if you would like to manage cuesheets automatically (like https://sourceforge.net/projects/dcue/ project). It is also up to user to provide good quality album cover images (e.g., see https://fanart.tv image library or https://covers.musichoarders.xyz cover search engine).

When a misformatted and ugly looking collection of music tracks is supplied with a proper bunch of cuesheets and cover images, `Audite.py` can suggest and carry out changes that will make an inveterate perfectionist smile!

Unfortunately, during the initial development of `Audite.py` some entropy has leaked into the source code. In spite of being chaos exterminator, `Audite.py` has become somewhat messy itself.

Consult `--help` letter and comment header within `Audite.py` for further details on script usage and implemented formatting rules.

### Dependencies

The versions of packages listed below are sufficient but not strictly necessary to run this script. It may work with older versions as well.

* [Python](https://www.python.org/) 3.13.7, including [subprocess](https://docs.python.org/3/library/subprocess.html), [functools](https://docs.python.org/3/library/functools.html), [difflib](https://docs.python.org/3/library/difflib.html) packages
* [FFmpeg](https://ffmpeg.org/) n8.0, providing `ffmpeg` and `ffprobe` utilities
* [ImageMagick](https://imagemagick.org/) 7.1.2-5, providing `magick` and `identify` utilities
* [FLAC](https://xiph.org/flac/index.html) 1.5.0, providing `metaflac` utility
* [Mutagen](https://github.com/quodlibet/mutagen) 1.47.3, providing `mid3v2` and `mutagen-inspect` utilities
* [mp3gain](https://sourceforge.net/projects/mp3gain/) 1.6.2, providing `mp3gain` utility
* [file](https://github.com/file/file) 5.46, generic Unix utility
* [which](https://www.gnu.org/software/coreutils/) 2.23, GNU core utility

## Playlister.py

Once a local/self-hosted audio library has been established and nicely formatted by `Audite.py`, one would take pleasure of listening to music tracks and sorting them into playlists. A playlist may be:
1. a folder with symbolic links pointing to favorite audio files
2. an M3U text file with paths to the same audio files

When the same playlist is represented by different means (perhaps, on different devices), it soon becomes desirable to synchronize them.

`Playlister.py` is intended to:
* **1st scenario:** read symbolic links from a directory, translate them into a listing of audio files and update an existing M3U list with their paths
* **2nd scenario:** read an existing M3U list, construct symbolic links to audio files from its entries and append these into an existing folder
* optionally sort the M3U list
* optionally rename symbolic links to get them nicely sorted by Artist, Album, Track no.
* report the counts of duplicates, broken links, etc. detected in the course of synchronization
* interactively ask for user intervention in some cases

Note that `Playlister.py` is currently designed to only **extend** playlists, it never deletes existing entries. This mirrors the growing nature of playlists, however deleting capability might be implemented later. Manual deletion of entries is usually sufficient for everyday playlist management.

Consult `--help` letter and comment header within `Playlister.py` for further details on script usage in both scenarios.

### Dependencies

The versions of packages listed below are sufficient but not strictly necessary to run this script. It may work with older versions as well.

* [Python](https://www.python.org/) 3.13.7, including [subprocess](https://docs.python.org/3/library/subprocess.html), [functools](https://docs.python.org/3/library/functools.html) packages
* [which](https://www.gnu.org/software/coreutils/) 2.23, [ln](https://www.gnu.org/software/coreutils/) 9.8, [sort](https://www.gnu.org/software/coreutils/) 9.8 $-$ GNU core utilities