#!/usr/bin/python

'''
   This script takes base directory (associated with music band or an album) with either a collection of
   subfolders (albums) or an ensemble of files (tracks).
   The goal is to format folder and album names, folder contents and file metadata in a standardized
   self-consistent way. The STANDARD is:
   1. Each album should be named as
         'YYYY - Album Name'
      where 'YYYY' is a four-digit year and 'Album Name' is a properly formatted album title (see '8. Title formatting' below)
   2. Each album contains several tracks and auxiliary files, such as a cuesheet '.cue' file [MANDATORY] and an album cover
      image 'cover.jpg' (square or slightly rectangular with 1000px height, typically 300-800 KiB) and (optionally) other
      arbitrary images, i.e. high-resolution 'Cover (larger).jpg' (typically > 1 MiB in size).
      When cuesheet is missing or damaged, Audite will do its best to reconstruct the cuesheet. Anyway, in these situations
      user should manually verify the reconstructed cuesheet and correct it if needed.
   3. Each track should be named as
         'XX. Track Name.ext'
      where 'XX' is a one-, two-, three- or four-digit track name (depending on the total number of tracks in the album),
      'Track Name' is a properly formatted track title (see '8. Title formatting' below) and 'ext' is a supported filetype
      extension ('flac' or 'mp3' only, 'm4a' will be converted into 'flac').
      IMPORTANT: track names and track numbering must be consistent with cuesheet file (which is mandatory for every album).
      IMPORTANT: each audiofile must contain proper technical data to be correctly decoded by modern mediaplayers (e.g. MPV player)
   4. Metadata of each audiofile must be consistent with that defined in the cuesheet file. The following entries must be present:
         FLAC: TRACKNUMBER, TRACKTOTAL, TITLE, ARTIST, ALBUM, DATE, GENRE, IMAGE (embedded)
          MP3: \-------- TRCK -------/, TIT2,  TPE1,   TALB,  TDRC, TCON,  APIC
      Other metadata is optional, but every mandatory entry must be unique.
      APPLICATION and SEEKTABLE blocks should be deleted from FLAC files. PADDING can also be deleted safely.
   5. Audiofile name must coincide with 'TITLE' entry apart from hieroglyphs and special characters that are unstable on
      filesystems EXT4, FAT32, NTFS, ExFAT. These characters should be replaced as follows (using UTF-8):
         0       ''
         '\n'    ''
         '\r'    ''
         '?'     '？'
         '\t'    ' '
         '/'     '∕'
         '\'     '∖'
         '|'     '∣'
         '$'     '＄'
         ':'     '.'
         '*'     '＊'
         '>'     '〉'
         '<'     '〈'
   6. The name of root directory must be consistent with band name as well (but can be only renamed by user, not within this script)
   7. Every track must contain REPLAY GAIN information:
     * FLAC: metaflac --add-replay-gain *.flac  # Apply to all tracks in album at once
         this sets tags: REPLAYGAIN_REFERENCE_LOUDNESS, REPLAYGAIN_TRACK_GAIN, REPLAYGAIN_TRACK_PEAK, REPLAYGAIN_ALBUM_GAIN, REPLAYGAIN_ALBUM_PEAK
     * MP3:  mp3gain -r -q -c -t *.mp3          # Apply to all tracks in album at once
         this modifies internal MP3 chunk volume scalers, without distorting the audiodata
   8. Title formatting:
      It's a bit of mess here, better see 'coerceTitle(...)' function below. Some key ideas are listed below (8a, 8b).
   8a. Title formatting (English words):
      8a.1 major words are capitalized: nouns, verbs, adjectives, adverbs + words from RECAP_TABLE below
      8a.2 the first word of each phrase is capitalized, a new phrase starts after symbols  .  /  |  \  -  ~  :
      8a.3 minor words are put into lower-case, including words from DECAP_TABLE below
      8a.4 some 'words' are put into upper-case, see UPPER_TABLE below
      If any of these rules contradict, prioritize them as listed above
   8b. Title formatting (non-English words):
      8b.1 the first word of each phrase is capitalized
      8b.2 other words are typically left 'as is'
      8b.3 user manually ensures German Nouns to be capitalized as well as Proper Names
   9. Audite might have bugs to be revealed yet. Stick to common sense if confused.
'''

def ShowHelp():
    print(
'''

 This is Audite programme.
 Audite is dedicated to help you with unification of an audio library.
 Audite processes either one artist or one album per session.

 Basic usage scenarios are the following:

 Scenario A: process one ARTIST (scan and unify a collection of albums by single artist)
 A1. Verify the uniformity of data under '/path/to/Some Artist' folder:
       -------------------------------------------------------------------------------
       python '/path/to/Audite.py' '/path/to/Some Artist' | tee '/path/to/logfile.log'
       -------------------------------------------------------------------------------
 A2. Then, if you agree with all the suggested changes, implement them:
       ----------------------------------------------------------------------------------------
       python '/path/to/Audite.py' '/path/to/Some Artist' --coerce | tee '/path/to/logfile.log'
       ----------------------------------------------------------------------------------------

 Scenario B: process one ALBUM (scan and unify only a single album or just a folder with tracks)
 B1. Verify the uniformity of data under '/path/to/Some Album' folder only:
       ---------------------------------------------------------------------------------------------
       python '/path/to/Audite.py' '/path/to/Some Album' --single-album | tee '/path/to/logfile.log'
       ---------------------------------------------------------------------------------------------
 B2. Then, if you agree with all the suggested changes, implement them:
       ------------------------------------------------------------------------------------------------------
       python '/path/to/Audite.py' '/path/to/Some Album' --single-album --coerce | tee '/path/to/logfile.log'
       ------------------------------------------------------------------------------------------------------

 Please, note: Audite spams plenty of output, so tee logfiles as
    suggested above to examine them in your favourite text viewer.

 And that's it. Nothing will get modified without the '--coerce' option.

 However, you might need these options to adjust the Audite's behaviour:
    --help            # Show this help letter
    --coerce          # Implement previously suggested changes (default: dry run mode)
    --single-album    # Treat the 1st argument as a path to an album (default: as a path to an artist)
    --unify-composer  # Enable checking and unification of COMPOSER tags in all audio files
    --no-cap          # Disable smart capitalisation of track and album titles (default: enabled)
                        This option is useful e.g. for tracks and albums entitled in German/Russian/Japanese etc.
    --skip-replaygain # Do not check nor unify REPLAYGAIN_* tags in any audio files
                        This option is useful e.g. for MP3 tracks which have already been replaygained
    --min-tracks=...  # Set the minimal count of audio files in a subfolder to be treated as album
                        This option is useful to make Audite skip small subfolders and do not check nor unify them
    --artist='...'    # Force the value of ARTIST tags in all audio files
    --album='...'     # Force the value of ALBUM tags in all audio files (allowed in '--single-album' mode only)
    --composer='...'  # Force the value of COMPOSER tags in all audio files (requires '--unify-composer' option)
    --year='...'      # Force the value of YEAR tags in all audio files
    --genre='...'     # Force the value of GENRE tags in all audio files

 Please, find the definition of what 'unified' is expected to be
    at the very beginning of 'Audite.py' file. Audite will do its
    best to unify audio library according to those recommendations.

 Please note, that Audite readily examines cuesheets ('.cue' files)
    under any album folder. Therefore, in the most difficult situations
    it helps a lot if you manually correct the problematic cuesheets.

''')

import sys
import os
import subprocess as proc
from datetime import date
import functools
from difflib import SequenceMatcher
import random

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Global fields
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

NOW_YEAR = date.today().year
SAFE_TABLE = str.maketrans("\t/\\|$?:*<>", ' ∕∖∣＄？.＊〈〉', "\n\r\0")
MAX_TRACKS = 9999   # Per album
DECAP_TABLE = ["a", "an", "the", "on", "in", "to", "onto", "into", "from", "with", "without", "for", "of", "and", "or", "nor", "not", "but", "yet", "as", "so", "feat", "featuring", "featured", "alt", "st", "nd", "rd", "th"]
RECAP_TABLE = ["i", "my", "me", "you", "your", "yours", "she", "her", "hers", "he", "his", "him", "they", "their", "theirs", "them", "we", "our", "ours", "us", "be", "am", "is", "are", "were", "was", "go", "do", "don't" "does", "doesn't", "did", "didn't", "done", "deja", "vu", "mr", "ms", "mrs", "dr", "yes", "no", "oh", "ah", "eh", "uh", "na", "ni", "li", "pt", "ho", "wa", "wo", "ma", "ed", "op", "nr", "can", "can't", "ad"]
UPPER_TABLE = ["ac/dc", "u2", "o2", "h2o", "co2", "sf", "ost", "dna", "t.n.t.", "tnt", "mtv", "s.o.s.", "sos", "i.r.s.", "r.i.p.", "rip", "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx", "xxi", "xxx", "mmxi", "mmxiv", "mcmxlv", "mcmlxxiv", "mmv", "cd", "ok", "bp", "sp", "t.v.", "uk", "u.k.", "usa", "tv", "fx", "xs", "sfso", "bbc", "htts", "jlt", "bwv", "bwu", "fff", "rpp", "b", "c", "d", "f", "g", "u", "r", "s", "y", "z", "nwobhm", "jfk", "gj", "aov"]

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Global functions
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

def myCap(word: str):
    if word[0].isalnum():
        return word.capitalize()
    else:
        return word[0] + word[1:].capitalize()

def coerceTitle(title: str):
    # Use triple dots
    pos = title.find("...")
    if pos >= 0:
        title = title[:pos] + "…" + title[pos+3:]
    # Split title into words
    preWords = title.strip().split(' ')
    words = []
    for w in preWords:
        if len(w) > 0:  # Skip empty strings (which appear if 'title' contained adjacent spaces)
            words.append(w)
    # Decapitalize auxiliary words (except the first one)
    for i in range(len(words)):
        word = words[i]
        if (len(word) >= 3 and not word[1:-1].isalpha()) or (len(word) <= 2 and not word.isalpha()):
            continue    # Do not process non-words
        wLow = word.lower()
        atSentStart = (i == 0) or (i > 0 and words[i-1][-1] in ['.', '/', '|', '\\', '-', '~', ':'])
        if noCaps:
            # If '--no-cap' mode is on, process (and capitalize) only the sentence-beginning words
            # ~ if atSentStart:
                # ~ words[i] = myCap(word)
            pass
        else:
            # In standard mode process every word
            # Escape the first and the last non-alphabetic characters
            if not wLow[0].isalpha():
                wLow = wLow[1:]
                if len(wLow) == 0:
                    continue
            if not wLow[-1].isalpha():
                wLow = wLow[:-1]
                if len(wLow) == 0:
                    continue
            # Apply capitalization where needed
            if wLow in DECAP_TABLE and not atSentStart:
                words[i] = word.lower()
            elif wLow in RECAP_TABLE:
                words[i] = myCap(word)
            elif wLow in UPPER_TABLE:
                words[i] = word.upper()
            elif len(wLow) <= 2 and not atSentStart:
                words[i] = word.lower()
            else:
                words[i] = myCap(word)
    return ' '.join(words)

def ensureStringSafety(fName: str):
    return fName.translate(SAFE_TABLE)

def canBeAlbum(dName: str, *, insideComplex: bool = False):
    numTracks = 0
    if os.path.isdir(dName):
        baseDname = os.path.basename(dName)
        if baseDname.find("- ") >= 0 or baseDname.find(". ") >= 0 or singleAlbum or insideComplex or "Misc" == baseDname or "Bonus CD" == baseDname: # Regular album must contain '-' in its dir name
            for elem in os.listdir(dName):
                fullPath = os.path.join(dName, elem)
                if os.path.isfile(fullPath) and isAudioFile(elem):
                    numTracks += 1
    return numTracks >= minTracks

def canBeComplexAlbum(dName: str):
    numAlbums = 0
    if os.path.isdir(dName):
        baseDname = os.path.basename(dName)
        if baseDname.find("- ") > 0 or baseDname.find(". ") > 0 or singleAlbum or "Misc" == baseDname:  # Album must contain '-' in its dir name
            for elem in os.listdir(dName):
                fullPath = os.path.join(dName, elem)
                if canBeAlbum(fullPath, insideComplex=True):
                    numAlbums += 1
    return numAlbums >= 2

def isAudioFile(fName: str):
    lastDot = fName.rfind(".")
    if lastDot < 0:
        return False
    else:
        fExt = fName[lastDot+1:].lower()
        return fExt in ["flac", "m4a", "mp3"]

def isCuesheet(fName: str):
    lastDot = fName.rfind(".")
    if lastDot < 0:
        return False
    else:
        fExt = fName[lastDot+1:].lower()
        return "cue" == fExt

def isImageFile(fName: str):
    lastDot = fName.rfind(".")
    if lastDot < 0:
        return False
    else:
        fExt = fName[lastDot+1:].lower()
        return "jpg" == fExt or "jpeg" == fExt or "png" == fExt or "bmp" == fExt or "webp" == fExt

def asymCrit(x, ref):
    if x < ref:
        return -10*(x/ref - 1)**2
    else:
        return -(x/ref - 1)**2

def nameCrit(strX: str):
    low = strX.lower()
    if low.find("cover") >= 0:
        return 0
    if low.find("folder") >= 0:
        return -1
    if low.find("front") >= 0:
        return -2
    if low.find("image") >= 0:
        return -5
    if low.find("artist") >= 0:
        return -100
    if low.find("logo") >= 0:
        return -110
    if low.find("back") >= 0:
        return -130

    return -50

def similar(strA: str, strB: str):
    return SequenceMatcher(None, strA, strB).ratio()

def getCommonPrefPostFixes(strs):
    minLen = min([len(s) for s in strs])
    # Find common prefixes
    commPref = ""
    for i in range(minLen):
        cs = set([s[+i] for s in strs])
        if len(cs) == 1:
            commPref = commPref + strs[0][i]
        else:
            break
    # Find common postfixes
    commPost = ""
    for i in range(1,minLen):
        cs = set([s[-i] for s in strs])
        if len(cs) == 1:
            commPost = strs[0][-i] + commPost
        else:
            break
    return commPref, commPost

def cutCueLine(line: str):
    line = line.strip()
    if '\r' == line[-1]:
        line = line[:-1].rstrip()
    if '"' == line[0]:
        line = line[1:-1].strip()
    return line

def isStringSafe(fName: str):
    return fName.isprintable() and fName.find('/') < 0 and fName.find('\\') < 0 and fName.find(':') < 0

def loadAndForceUTF8(fName: str):
    text = ""
    try:
        f = open(fName, 'r', encoding='utf-8')
        text = f.read()
    except:
        f.close()
        f = open(fName, 'r', encoding='cp1251')
        text = f.read()
        f.close()
        # Reencode file contents with UTF-8
        f = open(fName, 'w', encoding='utf-8')
        f.write(text)
    finally:
        f.close()
    return text

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Classes
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

class CoverImage:

    def __init__(self, parentDir, fileName):
        # Define class fields
        self.albumPath = ""
        self.imageFile = ""
        self.fullPath = ""
        #
        self.name = ""
        self.ext = ""
        self.width = 0
        self.height = 0
        self.bestWH = 0
        self.quality = 0
        self.suitability = 0
        self.fileSize = 0
        #
        self.strStatus = ""
        self.needsRename = True
        self.needsResize = True

        # Setup cover image
        self.albumPath = parentDir
        self.imageFile = fileName
        self.fullPath = os.path.join(parentDir, fileName)
        assert os.path.isfile(self.fullPath)

        # Analyze image file
        dotPos = fileName.rindex('.')
        self.ext = fileName[dotPos+1:]
        self.name = fileName[:dotPos]
        imgProps = os.popen(f'identify -format "%w %h %Q %b" -precision 16 "{self.fullPath}"').read().split(" ")
        imgProps[3] = imgProps[3][:-1]
        assert(len(imgProps) == 4)
        assert(imgProps[0].isnumeric())
        assert(imgProps[1].isnumeric())
        assert(imgProps[2].isnumeric())
        assert(imgProps[3].isnumeric())
        self.width = int(imgProps[0])
        self.height = int(imgProps[1])
        self.quality = int(imgProps[2])
        self.fileSize = int(imgProps[3])
        if self.quality == 0:
            self.quality = 80
        self.suitability = asymCrit(self.width, 1000) + asymCrit(self.height, 1000) + nameCrit(self.name) + asymCrit(self.quality, 80)

        # Check status
        self.needsRename = (self.ext != "jpg") or (self.name != "cover")
        self.needsResize = (self.width > 1000) or (self.height > 1000) or (self.width != self.height) or (self.quality > 89) # 89 instead of 80 to avoid useless JPEG recompressions
        self.bestWH = min(min(self.width,1000), min(self.height,1000))
        if self.needsRename:
            self.strStatus += f"\n\t+ imperfect image name '{self.imageFile}', suggested 'cover.jpg'"
        if self.needsResize:
            self.strStatus += f"\n\t+ imperfect image dimensions ({self.width}x{self.height} @ {self.quality}%), suggested {self.bestWH}x{self.bestWH} @ 80%"
        if self.isOk():
            self.strStatus += f"\n\t* Cover image {self.width}x{self.height} @ {self.quality}% '{self.fullPath}' STATUS: OK"

    def isNormal(self):
        return self.width > 0 and self.height > 0 and self.quality > 0 and len(self.name) > 0 and len(self.ext) > 0

    def isOk(self):
        return not (self.needsRename or self.needsResize)

    def __gt__(self, other):
        return self.suitability > other.suitability

    def coerce(self):
        print(f"\t* Coercing cover image '{self.imageFile}':", end=" ")
        if self.isOk():
            print("OK, SKIPPED")
            return

        # Ensure proper cover image name
        if self.needsRename:
            newFullPath = os.path.join(self.albumPath, "cover.jpg") # Perfect path
            spareFullPath = ""
            if os.path.isfile(newFullPath): # If the perfect path is occupied by other (imperfect) image
                spareFullPath = os.path.join(self.albumPath, "cover (intermediate).jpg")   # temporary path
                os.rename(newFullPath, spareFullPath)
            # Rename perfect image into 'cover.jpg'
            os.rename(self.fullPath, newFullPath)
            if len(spareFullPath) > 0:
                os.rename(spareFullPath, self.fullPath) # exchange the other (imperfect) image with current's old path
            self.fullPath = newFullPath # Update cover image path
            self.needsRename = False
            print("renamed", end=" ")

        # Ensure proper cover image size
        if self.needsResize:
            newFullPath = os.path.join(self.albumPath, "Cover (larger).jpg") # Large-scale version of image
            os.rename(self.fullPath, newFullPath)
            strDims = f'{self.bestWH}x{self.bestWH}'
            proc.call(['magick', newFullPath, '-resize', strDims+'^', '-gravity', 'center', '-extent', strDims, '-quality', '80', self.fullPath])
            self.needsResize = False
            print("resized", end=" ")

        # Picture is coerced
        print("DONE")

class Track:

    def __init__(self, album, fileName, checkNum):
        # Define class fields
        self.albumPath = ""
        self.audioFile = ""
        self.fullPath = ""
        self.goodName = ""
        #
        self.number = 0
        self.name = ""
        self.album = None
        self.ext = ""
        self.codec = ""
        self.goodName = ""
        #
        self.metaNumber = 0
        self.metaTrackTotal = 0
        self.metaTitle = ""
        self.metaArtist = ""
        self.metaComposer = ""
        self.metaAlbum = ""
        self.metaDate = 0
        self.metaGenre = ""
        self.metaImageW = 0
        self.metaImageH = 0
        #
        self.strStatus = ""
        self.strMetaStatus = ""
        self.misnumbered = False
        self.needsReencode = False
        self.needsRename = False
        self.needsRemark = False
        self.needsReplayGain = False
        #
        self.renewPicture = False
        self.deleteApplication = False
        self.deleteSeektable = False
        self.deletePadding = False

        # Setup track
        self.album = album
        self.albumPath = self.album.fullPath
        self.audioFile = fileName
        self.fullPath = os.path.join(self.albumPath, fileName)
        assert os.path.isfile(self.fullPath)

        # Analyze audio file name
        dotPos = fileName.rindex('.')
        self.ext = fileName[dotPos+1:]
        numAndTitle = fileName[:dotPos].strip()
        if not numAndTitle[0].isdigit():
            self.name = numAndTitle
        else:
            namePos = 1
            while namePos < len(numAndTitle) and numAndTitle[namePos].isdigit():
                namePos += 1
            # Extract number and title from file name
            if namePos < len(numAndTitle) and (numAndTitle[namePos] in ['.','-',' '] or namePos < len(numAndTitle)/3.0):
                self.number = int(numAndTitle[:namePos])
                self.name = numAndTitle[namePos:].lstrip()
                if self.name[0] == '.' or self.name[0] == '-':
                    self.name = self.name[1:].lstrip()
                # Check if track number coincides with its index in album
                if checkNum != self.number:
                    self.misnumbered = True
                    self.strMetaStatus += f"\n\t\t+ suspicious track number '{self.number}', expected '{checkNum}'"
            else:
                self.name = numAndTitle

        # Analyze audio file contents and extract metadata from it
        stats = os.popen(f'file "{self.fullPath}"').read()
        if stats.find("FLAC") >= 0:
            self.codec = "flac"
            # FLAC audio length (in samples)
            strSamples = os.popen(f'metaflac --show-total-samples "{self.fullPath}"').read()
            if strSamples[0] == '0':
                self.needsReencode = True
                self.strMetaStatus += "\n\t\t+ missing audio length, reencoding required"
            strTags = os.popen(f'metaflac --show-all-tags "{self.fullPath}"').read()
            strTagsUpper = strTags.upper()
            # Parasitic tags
            pos = strTagsUpper.find("LOG=")
            if pos >= 0:
                self.needsRemark = True
            # FLAC track number
            pos = strTags.find("TRACKNUMBER=")
            if pos >= 0:
                end = strTags.index('\n',pos+12)
                strNumber = strTags[pos+12:end].strip()
                if strNumber.isnumeric():
                    self.metaNumber = int(strNumber)
                    if len(strNumber) != len(str(self.album.trackTotal)):
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ imperfect TRACKNUMBER tag format, suggested '{self.album.tNumFmt}'"
                else:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ invalid TRACKNUMBER tag '"+strNumber+"'"
                if strTagsUpper.count("TRACKNUMBER=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate TRACKNUMBER tag"
            else:
                self.needsRemark = True
                self.strMetaStatus += "\n\t\t+ missing TRACKNUMBER tag"
            # FLAC track total
            pos = strTags.find("TRACKTOTAL=")
            if pos >= 0:
                end = strTags.index('\n',pos+11)
                strTrackTot = strTags[pos+11:end].strip()
                if strTrackTot.isnumeric():
                    self.metaTrackTotal = int(strTrackTot)
                else:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ invalid TRACKTOTAL tag '"+strTrackTot+"'"
                if self.metaTrackTotal != self.album.trackTotal:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ TRACKTOTAL tag '{strTrackTot}' differs from CUE tag, priority for '{self.album.trackTotal}'"
                    self.metaTrackTotal = self.album.trackTotal
                if strTagsUpper.count("TRACKTOTAL=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate TRACKTOTAL tag"
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing TRACKTOTAL tag, suggested '{self.album.trackTotal}'"
                self.metaTrackTotal = self.album.trackTotal
            # FLAC title
            pos = strTags.find("TITLE=")
            if pos >= 0:
                end = strTags.index('\n',pos+6)
                self.metaTitle = strTags[pos+6:end].strip()
                if strTagsUpper.count("TITLE=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate TITLE tag"
            else:
                self.needsRemark = True
                self.strMetaStatus += "\n\t\t+ missing TITLE tag"
            # FLAC artist
            pos = strTags.find("ARTIST=")
            if pos >= 0:
                end = strTags.index('\n',pos+7)
                self.metaArtist = strTags[pos+7:end].strip()
                if ensureStringSafety(self.metaArtist) != ensureStringSafety(self.album.artist) and len(self.album.artist) > 0:
                    if self.album.artist.lower() != "various artists":
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ ARTIST tag '{self.metaArtist}' differs from album's artist, priority for '{self.album.artist}'"
                        self.metaArtist = self.album.artist
                if strTagsUpper.count("ARTIST=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate ARTIST tag"
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ARTIST tag, suggested '{self.album.artist}'"
                self.metaArtist = self.album.artist
            # FLAC composer
            if allowComposer:
                pos = strTags.find("COMPOSER=")
                if pos >= 0:
                    end = strTags.index('\n',pos+9)
                    self.metaComposer = strTags[pos+9:end].strip()
                    if ensureStringSafety(self.metaComposer) != ensureStringSafety(self.album.composer) and len(self.album.composer) > 0:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ COMPOSER tag '{self.metaComposer}' differs from album's composer, priority for '{self.album.composer}'"
                        self.metaComposer = self.album.composer
                    if strTagsUpper.count("COMPOSER=") > 1:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ duplicate COMPOSER tag"
                elif len(self.album.composer) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ missing COMPOSER tag, suggested '{self.album.composer}'"
                    self.metaComposer = self.album.composer
            # FLAC album
            pos = strTags.find("ALBUM=")
            if pos >= 0:
                end = strTags.index('\n',pos+6)
                self.metaAlbum = strTags[pos+6:end].strip()
                if ensureStringSafety(self.metaAlbum) != ensureStringSafety(self.album.title) and len(self.album.title) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ ALBUM '{self.metaAlbum}' differs from album's title, priority for '{self.album.title}'"
                    self.metaAlbum = self.album.title
                if strTagsUpper.count("ALBUM=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate ALBUM tag"
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ALBUM tag, suggested '{self.album.title}'"
                self.metaAlbum = self.album.title
            # FLAC date
            pos = strTags.find("DATE=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                strDate = strTags[pos+5:end].strip()
                if strDate.isnumeric():
                    self.metaDate = int(strDate)
                    if self.metaDate != self.album.year and 0 < self.album.year <= NOW_YEAR:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ DATE tag '{self.metaDate}' differs from album's year, priority for '{self.album.year:04d}'"
                        self.metaDate = self.album.year
                elif 0 < self.album.year <= NOW_YEAR:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ invalid DATE tag '{strDate}', suggested '{self.album.year:04d}'"
                    self.metaDate = self.album.year
                if strTagsUpper.count("DATE=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate DATE tag"
            elif 0 < self.album.year <= NOW_YEAR:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing DATE tag, suggested '{self.album.year:04d}'"
                self.metaDate = self.album.year
            # FLAC genre
            pos = strTags.find("GENRE=")
            if pos >= 0:
                end = strTags.index('\n',pos+6)
                self.metaGenre = strTags[pos+6:end].strip()
                if self.metaGenre != self.album.genre and len(self.album.genre) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ GENRE tag '{self.metaGenre}' differs from CUE tag, priority for '{self.album.genre}'"
                    self.metaGenre = self.album.genre
                if strTagsUpper.count("GENRE=") > 1:
                    self.needsRemark = True
                    self.strMetaStatus += "\n\t\t+ duplicate GENRE tag"
            elif len(self.album.genre) > 0:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing GENRE tag, suggested '{self.album.genre}'"
                self.metaGenre = self.album.genre
            # FLAC cover image
            strPic = os.popen(f'metaflac --list --block-type=PICTURE "{self.fullPath}" | head -n 9').read()
            if len(strPic) < 10:
                self.needsRemark = True
                self.renewPicture = True
                self.strMetaStatus += "\n\t\t+ missing PICTURE block"
            elif album.cover != None:
                if strPic.find("Cover") < 0 or strPic.find(f"width: {album.cover.bestWH}") < 0 or strPic.find(f"height: {album.cover.bestWH}") < 0 \
                        or strPic.find("image/jpeg") < 0:
                    self.needsRemark = True
                    self.renewPicture = True
                    self.strMetaStatus += "\n\t\t+ imperfect PICTURE block"
            # FLAC replay gain
            if not skipReplayGain:
                pos = strTags.find("REPLAYGAIN_REFERENCE_LOUDNESS")
                self.needsReplayGain |= (0 > pos)
                pos = strTags.find("REPLAYGAIN_TRACK_GAIN")
                self.needsReplayGain |= (0 > pos)
                pos = strTags.find("REPLAYGAIN_TRACK_PEAK")
                self.needsReplayGain |= (0 > pos)
                pos = strTags.find("REPLAYGAIN_ALBUM_GAIN")
                self.needsReplayGain |= (0 > pos)
                pos = strTags.find("REPLAYGAIN_ALBUM_PEAK")
                self.needsReplayGain |= (0 > pos)
                if self.needsReplayGain:
                    self.strMetaStatus += "\n\t\t+ missing FLAC replay gain information"
            # excessive FLAC blocks
            strBlock = os.popen(f'metaflac --list --block-type=SEEKTABLE "{self.fullPath}" | head -n 2').read()
            if len(strBlock) > 2:
                self.needsRemark = True
                self.deleteSeektable = True
                self.strMetaStatus += "\n\t\t+ worthless SEEKTABLE block will be removed"
            strBlock = os.popen(f'metaflac --list --block-type=APPLICATION "{self.fullPath}" | head -n 2').read()
            if len(strBlock) > 2:
                self.needsRemark = True
                self.deleteApplication = True
                self.strMetaStatus += "\n\t\t+ worthless APPLICATION block(s) will be removed"
            strBlock = os.popen(f'metaflac --list --block-type=PADDING "{self.fullPath}" | head -n 2').read()
            if len(strBlock) > 2:
                self.needsRemark = True
                self.deletePadding = True
                self.strMetaStatus += "\n\t\t+ worthless PADDING block(s) will be removed"
        elif stats.find("MPEG ADTS, layer III") >= 0:
            self.codec = "mp3"
            strTags = os.popen(f'mid3v2 -l "{self.fullPath}"').read()
            # MP3 track number/track total
            pos = strTags.find("TRCK=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                strTrck = strTags[pos+5:end].strip()
                pos = strTrck.find("/")
                if pos > 0:
                    strNumber = strTrck[:pos].strip()
                    if strNumber.isnumeric():
                        self.metaNumber = int(strNumber)
                        if len(strNumber) != len(str(self.album.trackTotal)):
                            self.needsRemark = True
                            self.strMetaStatus += f"\n\t\t+ imperfect TRCK number tag format, suggested '{self.album.tNumFmt}'"
                    else:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ invalid TRCK number tag '"+strNumber+"'"
                    strTotal = strTrck[pos+1:].strip()
                    if strTotal.isnumeric():
                        self.metaTrackTotal = int(strTotal)
                    else:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ invalid TRCK total tag '"+strTotal+"'"
                    if self.metaTrackTotal != album.trackTotal:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ TRCK total tag '{strTotal}' differs from CUE tag, priority for '{self.album.trackTotal}'"
                        self.metaTrackTotal = album.trackTotal
                    if len(strNumber) != len(strTotal):
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ imperfect TRCK tag '{strTrck}' (different number lengthes)"
                else:
                    if strTrck.isnumeric():
                        self.metaNumber = int(strTrck)
                    else:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ invalid TRCK tag '"+strNumber+"'"
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ missing TRCK (/track total) tag, suggested '{self.album.trackTotal}'"
                    self.metaTrackTotal = self.album.trackTotal
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing TRCK (track number/track total) tag, suggested track total '{self.album.trackTotal}'"
                self.metaTrackTotal = self.album.trackTotal
            # MP3 title
            pos = strTags.find("TIT2=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaTitle = strTags[pos+5:end].strip()
            else:
                self.needsRemark = True
                self.strMetaStatus += "\n\t\t+ missing TIT2 (title) tag"
            # MP3 artist
            pos = strTags.find("TPE1=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaArtist = strTags[pos+5:end].strip()
                if ensureStringSafety(self.metaArtist) != ensureStringSafety(self.album.artist) and len(self.album.artist) > 0:
                    if self.album.artist.lower() != "various artists":
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ TPE1 (artist) tag '{self.metaArtist}' differs from album's artist, priority for '{self.album.artist}'"
                        self.metaArtist = self.album.artist
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing TPE1 (artist) tag, suggested '{self.album.artist}'"
                self.metaArtist = self.album.artist
            # MP3 composer
            if allowComposer:
                pos = strTags.find("TCOM=")
                if pos >= 0:
                    end = strTags.index('\n',pos+5)
                    self.metaComposer = strTags[pos+5:end].strip()
                    if ensureStringSafety(self.metaComposer) != ensureStringSafety(self.album.composer) and len(self.album.composer) > 0:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ TCOM (composer) tag '{self.metaComposer}' differs from album's composer, priority for '{self.album.composer}'"
                        self.metaComposer = self.album.composer
                elif len(self.album.composer) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ missing TCOM (composer) tag, suggested '{self.album.composer}'"
                    self.metaComposer = self.album.composer
            # MP3 album
            pos = strTags.find("TALB=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaAlbum = strTags[pos+5:end].strip()
                if ensureStringSafety(self.metaAlbum) != ensureStringSafety(self.album.title) and len(self.album.title) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ TALB (album) tag '{self.metaAlbum}' differs from album's title, priority for '{self.album.title}'"
                    self.metaAlbum = self.album.title
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing TALB (album) tag, suggested '{album.title}'"
                self.metaAlbum = self.album.title
            # MP3 date
            pos = strTags.find("TDRC=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                strDate = strTags[pos+5:end].strip()
                if strDate.isnumeric():
                    self.metaDate = int(strDate)
                    if self.metaDate != self.album.year and 0 < self.album.year <= NOW_YEAR:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ TDRC (year) tag '{self.metaDate:04d}' differs from album's year, priority for '{self.album.year:04d}'"
                        self.metaDate = self.album.year
                else:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ strange TDRC (year) tag '{strDate}', suggested '{self.album.year:04d}'"
                    self.metaDate = self.album.year
            elif 0 < self.album.year <= NOW_YEAR:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing TDRC (year) tag, suggested '{self.album.year:04d}'"
                self.metaDate = self.album.year
            # MP3 genre
            pos = strTags.find("TCON=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaGenre = strTags[pos+5:end].strip()
                if self.metaGenre != self.album.genre and len(self.album.genre) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ TCON (genre) tag '{self.metaGenre}' differs from CUE tag, priority for '{self.album.genre}'"
                    self.metaGenre = self.album.genre
            elif len(self.album.genre) > 0:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing TCON (genre) tag, suggested '{self.album.genre}'"
                self.metaGenre = self.album.genre
            # MP3 cover image
            pos = strTags.find("APIC=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                picToks = strTags[pos+5:end].strip().split(' ')
                tok = ""
                for i in range(len(picToks)-1, -1, -1):
                    tok = picToks[i]
                    if tok.isnumeric():
                        break
                picFileSize = int(tok)
                if self.album.cover != None:
                    if not self.album.cover.isOk() or picFileSize != self.album.cover.fileSize:
                        self.needsRemark = True
                        self.renewPicture = True
                        self.strMetaStatus += "\n\t\t+ imperfect APIC (cover image) block"
            else:
                self.needsRemark = True
                self.renewPicture = album.cover != None
                self.strMetaStatus += "\n\t\t+ missing APIC (cover image)"
            # MP3 always needs replay gain check by default
            if not skipReplayGain:
                self.needsReplayGain = True
                self.strMetaStatus += "\n\t\t+ MP3 replay gain will be verified anyway"
        elif stats.find("ALAC") >= 0:
            self.codec = "m4a"
            # Deal with yet inacceptable ALAC
            self.strMetaStatus += "\n\t\t+ ALAC file format (.m4a) is not accepted yet, will be reencoded into FLAC (.flac)"
            #
            strTags = os.popen(f'mutagen-inspect "{self.fullPath}"').read()
            # MP4 track number/track total
            pos = strTags.find("trkn=(")
            if pos >= 0:
                end = strTags.index(')',pos+6)
                strTrck = strTags[pos+6:end].strip()
                pos = strTrck.find(",")
                if pos > 0:
                    strNumber = strTrck[:pos].strip()
                    if strNumber.isnumeric():
                        self.metaNumber = int(strNumber)
                        if len(strNumber) != len(str(self.album.trackTotal)):
                            self.needsRemark = True
                            self.strMetaStatus += f"\n\t\t+ imperfect ©TRKN number tag format, suggested '{self.album.tNumFmt}'"
                    else:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ invalid ©TRKN number tag '"+strNumber+"'"
                    strTotal = strTrck[pos+1:].strip()
                    if strTotal.isnumeric():
                        self.metaTrackTotal = int(strTotal)
                    else:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ invalid ©TRKN total tag '"+strTotal+"'"
                    if self.metaTrackTotal != album.trackTotal:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ ©TRKN total tag '{strTotal}' differs from CUE tag, priority for '{self.album.trackTotal}'"
                        self.metaTrackTotal = album.trackTotal
                    if len(strNumber) != len(strTotal):
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ imperfect ©TRKN tag '{strTrck}' (different number lengthes)"
                else:
                    if strTrck.isnumeric():
                        self.metaNumber = int(strTrck)
                    else:
                        self.needsRemark = True
                        self.strMetaStatus += "\n\t\t+ invalid ©TRKN tag '"+strNumber+"'"
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ missing ©TRKN (/track total) tag, suggested '{self.album.trackTotal}'"
                    self.metaTrackTotal = self.album.trackTotal
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ©TRKN (track number/track total) tag, suggested track total '{self.album.trackTotal}'"
                self.metaTrackTotal = self.album.trackTotal
            # MP4 title
            pos = strTags.find("\xa9nam=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaTitle = strTags[pos+5:end].strip()
            else:
                self.needsRemark = True
                self.strMetaStatus += "\n\t\t+ missing ©NAM (title) tag"
            # MP4 artist
            pos = strTags.find("\xa9ART=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaArtist = strTags[pos+5:end].strip()
                if ensureStringSafety(self.metaArtist) != ensureStringSafety(self.album.artist) and len(self.album.artist) > 0:
                    if self.album.artist.lower() != "various artists":
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ ©ART (artist) tag '{self.metaArtist}' differs from album's artist, priority for '{self.album.artist}'"
                        self.metaArtist = self.album.artist
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ©ART (artist) tag, suggested '{self.album.artist}'"
                self.metaArtist = self.album.artist
            # MP4 composer
            if allowComposer:
                pos = strTags.find("\xa9wrt=")
                if pos >= 0:
                    end = strTags.index('\n',pos+5)
                    self.metaComposer = strTags[pos+5:end].strip()
                    if ensureStringSafety(self.metaComposer) != ensureStringSafety(self.album.composer) and len(self.album.composer) > 0:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ ©WRT (composer) tag '{self.metaComposer}' differs from album's composer, priority for '{self.album.composer}'"
                        self.metaComposer = self.album.composer
                elif len(self.album.composer) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ missing ©WRT (composer) tag, suggested '{self.album.composer}'"
                    self.metaComposer = self.album.composer
            # MP4 album
            pos = strTags.find("\xa9alb=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaAlbum = strTags[pos+5:end].strip()
                if ensureStringSafety(self.metaAlbum) != ensureStringSafety(self.album.title) and len(self.album.title) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ ©ALB (album) tag '{self.metaAlbum}' differs from album's title, priority for '{self.album.title}'"
                    self.metaAlbum = self.album.title
            else:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ©ALB (album) tag, suggested '{album.title}'"
                self.metaAlbum = self.album.title
            # MP4 date
            pos = strTags.find("\xa9day=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                strDate = strTags[pos+5:end].strip()
                if strDate.isnumeric():
                    self.metaDate = int(strDate)
                    if self.metaDate != self.album.year and 0 < self.album.year <= NOW_YEAR:
                        self.needsRemark = True
                        self.strMetaStatus += f"\n\t\t+ ©DAY (year) tag '{self.metaDate:04d}' differs from album's year, priority for '{self.album.year:04d}'"
                        self.metaDate = self.album.year
                else:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ strange ©DAY (year) tag '{strDate}', suggested '{self.album.year:04d}'"
                    self.metaDate = self.album.year
            elif 0 < self.album.year <= NOW_YEAR:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ©DAY (year) tag, suggested '{self.album.year:04d}'"
                self.metaDate = self.album.year
            # MP4 genre
            pos = strTags.find("\xa9gen=")
            if pos >= 0:
                end = strTags.index('\n',pos+5)
                self.metaGenre = strTags[pos+5:end].strip()
                if self.metaGenre != self.album.genre and len(self.album.genre) > 0:
                    self.needsRemark = True
                    self.strMetaStatus += f"\n\t\t+ ©GEN (genre) tag '{self.metaGenre}' differs from CUE tag, priority for '{self.album.genre}'"
                    self.metaGenre = self.album.genre
            elif len(self.album.genre) > 0:
                self.needsRemark = True
                self.strMetaStatus += f"\n\t\t+ missing ©GEN (genre) tag, suggested '{self.album.genre}'"
                self.metaGenre = self.album.genre
            # MP4 cover image
            pos = strTags.find("covr=[")
            if pos >= 0:
                end = strTags.index(']',pos+6)
                picToks = strTags[pos+6:end].strip().split(' ')
                tok = ""
                for i in range(len(picToks)-1, -1, -1):
                    tok = picToks[i]
                    if tok.isnumeric():
                        break
                picFileSize = int(tok)
                if self.album.cover != None:
                    if not self.album.cover.isOk() or picFileSize != self.album.cover.fileSize:
                        self.needsRemark = True
                        self.renewPicture = True
                        self.strMetaStatus += "\n\t\t+ imperfect COVR (cover image) block"
            else:
                self.needsRemark = True
                self.renewPicture = album.cover != None
                self.strMetaStatus += "\n\t\t+ missing COVR (cover image)"
            # ALAC should be reencoded into FLAC and remarked anyway, picture reattached
            self.needsReencode = True
            self.needsRemark = True
            self.renewPicture = True
            self.needsReplayGain = not skipReplayGain   # Reencoded FLAC will need replay gain by default
            self.deletePadding = True
        else:
            self.strMetaStatus += f"\n\t\t+ STRANGE audiofile with unknown codec, stats '{stats}'"

        # Find track entry in the cuesheet and check metadata number and title revealed earlier
        # If cuesheet entry is not found, suggest optimal track number and title from file name, also check file name safety
        if len(self.album.cueEntries) == self.album.trackTotal and self.album.trackTotal > 0:
            # Find the best matching cue entry by complex criterion
            cueBestInd = 0
            cueBestScore = -1.0e6
            for cueInd in range(len(album.cueEntries)):
                cueNum = cueInd + 1
                cueTit = self.album.cueEntries[cueInd]
                score = 0
                if len(self.name) > 0:
                    score += 5 * similar(self.name.lower(), cueTit.lower())
                if len(self.metaTitle) > 0:
                    score += 3 * similar(self.metaTitle, cueTit)
                if self.number > 0 and not self.name.isascii():
                    score += -2 * (self.number - cueNum)**2 / 4
                if self.metaNumber > 0 and 0 == self.number and not self.name.isascii():
                    score += -1 * (self.metaNumber - cueNum)**2 / 4
                if score > cueBestScore:
                    cueBestScore = score
                    cueBestInd = cueInd
                # ~ print(cueNum, cueTit, score, self.number, self.metaNumber, self.name, self.metaTitle)
            # Compare track number and track title to that determined from cuesheet
            cueNumber = cueBestInd + 1
            cueTitle = self.album.cueEntries[cueBestInd]
            symbList = list(cueTitle)
            random.shuffle(symbList)
            self.album.cueEntries[cueBestInd] = '@!%=*/&^'.join(symbList)    # Avoid parasitic coincides in future searches
            self.strStatus = f"\n\t* Track {cueNumber:{self.album.tNumFmt}} '{cueTitle}' File '{self.audioFile}' STATUS: "
            bestName = ensureStringSafety(cueTitle)
            #
            if self.number != cueNumber:
                self.needsRename = True
                self.strStatus += f"\n\t\t+ file number conflicts with cuesheet track number, priority for {cueNumber:{self.album.tNumFmt}}"
            if self.name != bestName:
                self.needsRename = True
                self.strStatus += f"\n\t\t+ file title conflicts with cuesheet track title, priority for '{bestName}'"
            if self.metaNumber > 0:
                if self.metaNumber != cueNumber:
                    self.needsRemark = True
                    self.strStatus += f"\n\t\t+ metadata track number {self.metaNumber:{self.album.tNumFmt}} conflicts with cuesheet track number, priority for {cueNumber:{self.album.tNumFmt}}"
            if len(self.metaTitle) > 0:
                if self.metaTitle != cueTitle:
                    self.needsRemark = True
                    self.strStatus += f"\n\t\t+ metadata title '{self.metaTitle}' conflicts with cuesheet track title, priority for '{cueTitle}'"
            # Force good values
            self.number = cueNumber
            self.name = bestName
            self.metaNumber = cueNumber
            self.metaTitle = cueTitle
        else:
            # Some cue entries are missing (or missing cuesheet at all)
            bestTitle = coerceTitle(self.name)
            if self.number != self.metaNumber or 0 == self.number:
                self.number = checkNum
            #
            bestName = ensureStringSafety(bestTitle)
            self.strStatus = f"\n\t* Track {self.number:{self.album.tNumFmt}} '{bestTitle}' File '{self.audioFile}' STATUS: "
            #
            if self.name != bestName:
                self.needsRename = True
                self.strStatus += f"\n\t\t+ file title is imperfect, suggested '{bestName}'"
            if self.metaNumber != self.number:
                self.needsRemark = True
                if self.metaNumber > 0:
                    self.strStatus += f"\n\t\t+ metadata track number {self.metaNumber:{self.album.tNumFmt}} conflicts with file number, priority for {self.number:{self.album.tNumFmt}}"
                if self.number == 0:
                    self.strStatus += " (track number will be removed)"
            if len(self.metaTitle) > 0:
                if ensureStringSafety(self.metaTitle) != bestTitle:
                    self.needsRemark = True
                    self.strStatus += f"\n\t\t+ metadata title '{self.metaTitle}' conflicts with file title, priority for '{bestTitle}'"
                else:
                    bestTitle = self.metaTitle
            # Enforce better values
            self.name = bestName
            self.metaNumber = self.number
            self.metaTitle = bestTitle

        # Merge status strings
        self.strStatus += self.strMetaStatus

        # Check file naming again
        newCodec = self.codec
        if "m4a" == newCodec:
            newCodec = "flac"
        if self.number > 0:
            self.goodName = f"{self.number:{self.album.tNumFmt}}. {self.name}.{newCodec}"
        else:
            self.goodName = self.name+"."+newCodec
        if self.audioFile != self.goodName:
            self.needsRename = True
            self.strStatus += f"\n\t\t+ file name '{self.audioFile}' is imperfect, suggested '{self.goodName}'"

        # 'OK' status
        if self.isOk():
            self.strStatus += "OK"
        else:
            self.strStatus += f"\n\t\t= {self.metaNumber:{self.album.tNumFmt}}/{self.metaTrackTotal} '{self.metaTitle}' by '{self.metaArtist}' in '{self.metaAlbum}' ({self.metaDate:04d}), style: '{self.metaGenre}'"

    def isNormal(self):
        return len(self.codec) > 0

    def isOk(self):
        return self.isNormal() and not (self.misnumbered or self.needsReencode or self.needsRename or self.needsRemark or self.needsReplayGain)

    def coerce(self):
        print(f"\t* Coercing track {self.metaNumber:{self.album.tNumFmt}} '{self.metaTitle}':", end=" ")
        if self.isOk():
            print("OK, SKIPPED")
            return

        # Reencode if needed
        if self.needsReencode:
            if "flac" == self.codec or "m4a" == self.codec:
                newFullPath = os.path.join(self.albumPath, "tmp.flac")
                res, err = proc.Popen(["ffmpeg", "-hide_banner", "-y", "-v", "error", "-i", self.fullPath, "-acodec", "flac", "-map_metadata", "0", newFullPath], stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
            elif "mp3" == self.codec:
                newFullPath = os.path.join(self.albumPath, "tmp.mp3")
                res, err = proc.Popen(["ffmpeg", "-hide_banner", "-y", "-v", "error", "-i", self.fullPath, "-acodec", "libmp3lame", "-map_metadata", "0", newFullPath], stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
            # Check reencoding result
            if len(err) == 0:
                os.remove(self.fullPath)    # Delete old file if reencoding was successful
                self.fullPath = newFullPath
                self.needsReencode = False
                self.needsRename = True
                if "m4a" == self.codec:
                    self.codec = "flac"
                print("reencoded", end=" ")
            else:
                print(f"\nERROR when reencoding '{self.fullPath}' into '{newFullPath}', report from FFMPEG reads:\n"+err)
                # If reencoding ALAC into FLAC failed, leave ALAC with .m4a extension
                if "m4a" == self.codec:
                    if self.number > 0:
                        self.goodName = f"{self.number:02d}. {self.name}.m4a"
                    else:
                        self.goodName = self.name+".m4a"
                    print(f"Leaving ALAC file '{self.fullPath}' with its own extension, since reencoding failed. No metadata will be updated")
                    self.needsRemark = False

        # Rename if needed
        if self.needsRename:
            newFullPath = os.path.join(self.albumPath, self.goodName)
            os.rename(self.fullPath, newFullPath)
            self.fullPath = newFullPath
            self.audioFile = self.goodName
            self.needsRename = False
            print("renamed", end=" ")

        # Update metadata if needed
        if self.needsRemark:
            if "flac" == self.codec:
                # Rewrite FLAC metadata
                proc.call(['metaflac', '--remove-tag=LOG', '--remove-tag=log', '--remove-tag=TRACKNUMBER', '--remove-tag=TRACKTOTAL', \
                            '--remove-tag=TOTALTRACKS', '--remove-tag=TITLE', '--remove-tag=ARTIST', '--remove-tag=ALBUMARTIST', \
                            '--remove-tag=ALBUM ARTIST', '--remove-tag=PERFORMER', '--remove-tag=ALBUM', '--remove-tag=GENRE', \
                            self.fullPath])
                proc.call(['metaflac',f'--set-tag=TRACKNUMBER={self.metaNumber:{self.album.tNumFmt}}', \
                            f'--set-tag=TRACKTOTAL={self.metaTrackTotal}', f'--set-tag=TITLE={self.metaTitle}', \
                            f'--set-tag=ARTIST={self.metaArtist}', f'--set-tag=ALBUM={self.metaAlbum}', \
                            f'--set-tag=GENRE={self.metaGenre}', self.fullPath])
                if 0 < self.metaDate <= NOW_YEAR:
                    proc.call(['metaflac', '--remove-tag=DATE', '--remove-tag=YEAR', self.fullPath])
                    proc.call(['metaflac', f'--set-tag=DATE={self.metaDate}', self.fullPath])
                if allowComposer and len(self.metaComposer) > 0:
                    proc.call(['metaflac', '--remove-tag=COMPOSER', self.fullPath])
                    proc.call(['metaflac', f'--set-tag=COMPOSER={self.metaComposer}', self.fullPath])
                print("remarked", end=" ")
                # Manage FLAC picture
                if self.renewPicture:
                    if self.album.cover != None and self.album.cover.isOk():
                        proc.call(['metaflac', '--remove', '--block-type=PICTURE', self.fullPath])
                        proc.call(['metaflac', f'--import-picture-from={self.album.cover.fullPath}', self.fullPath])
                        self.renewPicture = False
                        print("repictured", end=" ")
                # Manage other FLAC blocks
                if self.deleteApplication:
                    proc.call(['metaflac', '--remove', '--block-type=APPLICATION', self.fullPath])
                    self.deleteApplication = False
                    print("del(FLAC.APPL)", end=" ")
                if self.deleteSeektable:
                    proc.call(['metaflac', '--remove', '--block-type=SEEKTABLE', self.fullPath])
                    self.deleteSeektable = False
                    print("del(FLAC.SEEK)", end=" ")
                # Strip FLAC padding
                if self.deletePadding:
                    proc.call(['metaflac', '--sort-padding', self.fullPath])
                    proc.call(['metaflac', '--dont-use-padding', '--remove', '--block-type=PADDING', self.fullPath])
                    self.deletePadding = False
                    print("del(FLAC.PADD)", end=" ")
                # Finished with FLAC remarking
                self.needsRemark = False
            elif "mp3" == self.codec:
                # Rewrite MP3 metadata
                proc.call(['mid3v2', '-T', f'{self.metaNumber:{self.album.tNumFmt}}/{self.metaTrackTotal}', '-t', self.metaTitle, '-a', self.metaArtist, \
                            '-A', self.metaAlbum, '-y', str(self.metaDate), '-g', self.metaGenre, self.fullPath])
                if allowComposer and len(self.metaComposer) > 0:
                    proc.call(['mid3v2', '--TCOM', self.metaComposer, self.fullPath])
                print("remarked", end=" ")
                # Manage MP3 picture
                if self.renewPicture:
                    if self.album.cover != None and self.album.cover.isOk():
                        proc.call(['mid3v2', '--delete-frames=APIC', self.fullPath])
                        proc.call(['mid3v2', '-p', self.album.cover.fullPath, self.fullPath])
                        self.renewPicture = False
                        print("repictured", end=" ")
                # Finished with MP3 remarking
                self.needsRemark = False
            else:
                print(f"CODEC '{self.codec}' SKIPPED", end="")

        # Track is coerced
        print("DONE")

class Album:

    def __init__(self, fullAlbumPath):
        # Define class fields
        self.rootDir = ""
        self.dirName = ""
        self.fullPath = ""
        self.goodName = ""
        #
        self.year = 0
        self.name = ""      # The perfect name for album directory
        self.title = ""     # The perfect album title for track metadata
        self.artist = ""
        self.composer = ""
        self.genre = ""
        self.trackTotal = 0
        self.tNumFmt = "02d"
        #
        self.cuesheet = ""
        self.cuetext = ""
        self.cueEntries = []
        self.manyCues = False
        self.cover = None
        self.tracks = []
        #
        self.strStatus = ""
        self.tracksOk = False
        self.needsReplayGain = False
        self.allOk = False
        #
        self.needsRename = False
        self.needsRecue = False

        # Common album setup
        self.fullPath = fullAlbumPath
        self.dirName = os.path.basename(self.fullPath)
        self.rootDir = os.path.dirname(self.fullPath)

        # Check defined metadata
        if len(albumTitle) > 0:
            self.title = albumTitle
            self.name = ensureStringSafety(self.title)
        if len(bandName) > 0:
            self.artist = bandName
        if len(composerName) > 0:
            self.composer = composerName
        if albumYear != 0:
            self.year = albumYear
        if len(albumGenre) > 0:
            self.genre = albumGenre

        # Find cuesheet file
        albContents = sorted(os.listdir(self.fullPath))
        cueSize = 0
        for fName in albContents:
            cuePath = os.path.join(self.fullPath, fName)
            if isCuesheet(fName) and os.path.isfile(cuePath):
                if len(self.cuesheet) > 0:
                    self.manyCues = True
                    thisCueSize = os.path.getsize(cuePath)
                    if thisCueSize > cueSize:
                        self.cuesheet = fName
                        cueSize = thisCueSize
                else:
                    self.cuesheet = fName
        if 0 == len(self.cuesheet):
            self.strStatus += "\n\t+ cuesheet is missing"
            self.needsRecue = True
        else:
            if self.manyCues:
                self.strStatus += "\n\t+ too many cuesheets, priority for '"+self.cuesheet+"'"

            # Read cuesheet file
            cueFullPath = os.path.join(self.fullPath, self.cuesheet)
            self.cuetext = loadAndForceUTF8(cueFullPath)
            if len(self.cuetext) == 0:
                self.strStatus += f"\n\t+ cuesheet file '{self.cuesheet}' is empty"
            else:
                # Check album title from cuesheet
                if 0 == len(self.title):
                    pos = self.cuetext.find('TITLE ')
                    if pos < 0:
                        self.strStatus += '\n\t+ missing album TITLE "..." in cuesheet, please add one'
                    else:
                        end = self.cuetext.index('\n', pos+6)
                        cueStr = cutCueLine(self.cuetext[pos+6:end])
                        self.title = coerceTitle(cueStr)
                        self.name = ensureStringSafety(self.title)
                        if 0 == len(self.title):
                            self.strStatus += "\n\t+ empty TITLE in cuesheet, please fill it in"
                        else:
                            self.strStatus += f"\n\t+ album title deduced from cuesheet: '{self.title}'"

                # Check year from cuesheet
                if 0 == self.year:
                    pos = self.cuetext.find('REM DATE ')
                    if pos < 0:
                        self.strStatus += "\n\t+ missing REM DATE in cuesheet, please add one"
                    else:
                        end = self.cuetext.index('\n', pos+9)
                        remDate = cutCueLine(self.cuetext[pos+9:end])
                        if not remDate.isnumeric():
                            self.strStatus += "\n\t+ invalid chars '"+remDate+"' after REM DATE in cuesheet"
                        else:
                            self.year = int(remDate)
                            self.strStatus += f"\n\t+ album year deduced from cuesheet: {self.year}"

                # Extract genre from cuesheet
                if 0 == len(self.genre):
                    pos = self.cuetext.find('REM GENRE ')
                    if pos < 0:
                        self.strStatus += '\n\t+ missing REM GENRE "..." in cuesheet, please add one'
                    else:
                        end = self.cuetext.index('\n', pos+10)
                        self.genre = cutCueLine(self.cuetext[pos+10:end])
                        if len(self.genre) == 0:
                            self.strStatus += "\n\t+ empty REM GENRE in cuesheet, please fill it in"
                        else:
                            self.strStatus += f"\n\t+ album genre deduced from cuesheet: '{self.genre}'"

                # Extract artist from cuesheet
                if 0 == len(self.artist):
                    pos = self.cuetext.find('PERFORMER ')
                    if pos < 0:
                        self.strStatus += '\n\t+ missing PERFORMER "..." in cuesheet, please add one'
                    else:
                        end = self.cuetext.index('\n', pos+10)
                        self.artist = cutCueLine(self.cuetext[pos+10:end])
                        if 0 == len(self.artist):
                            self.strStatus += "\n\t+ empty PERFORMER in cuesheet, please fill it in"
                        else:
                            self.strStatus += f"\n\t+ album artist deduced from cuesheet: '{self.artist}'"

                # Extract composer from cuesheet
                if allowComposer and 0 == len(self.composer):
                    pos = self.cuetext.find('REM COMPOSER ')
                    if pos >= 0:
                        end = self.cuetext.index('\n', pos+13)
                        self.composer = cutCueLine(self.cuetext[pos+13:end])
                        if 0 == len(self.artist):
                            self.strStatus += "\n\t+ empty REM COMPOSER in cuesheet, please fill it in"
                        else:
                            self.strStatus += f"\n\t+ album composer deduced from cuesheet: '{self.composer}'"

                # Extract tracktotal from cuesheet
                trackTotalPos = self.cuetext.rfind('TRACK ')
                if trackTotalPos < 0:
                    self.strStatus += '\n\t+ missing TRACKs in cuesheet, please add some'
                else:
                    end = self.cuetext.index(' ', trackTotalPos+6)
                    trackTot = self.cuetext[trackTotalPos+6:end].strip()
                    if not trackTot.isnumeric():
                        self.strStatus += "\n\t+ invalid chars '"+trackTot+"' after the last TRACK in cuesheet"
                    else:
                        cueTrackTotal = int(trackTot)
                        if cueTrackTotal < 1 or cueTrackTotal > MAX_TRACKS:
                            self.strStatus += f"\n\t+ unsupported track number {cueTrackTotal}"
                        else:
                            self.trackTotal = cueTrackTotal

                # Build the list of track entries from the cuesheet
                pos = 0
                for i in range(self.trackTotal):
                    pos1 = self.cuetext.find('TRACK ', pos)
                    if pos1 < 0:
                        break
                    pos = pos1+6
                    end = self.cuetext.find(' ', pos)
                    trackNo = self.cuetext[pos:end].strip()
                    if trackNo.isnumeric():
                        tInd = int(trackNo)
                        if i+1 != tInd:
                            self.strStatus += f"\n\t+ suspicious track number '{tInd}' in cuesheet, expected '{i+1}'"
                    else:
                        break
                    pos1 = self.cuetext.find('TITLE ', pos) # Position of track title
                    pos2 = self.cuetext.find('TRACK ', pos) # Position of the next track
                    if pos2 < 0:
                        pos2 = len(self.cuetext)
                    if pos1 > 0 and pos1 < pos2:
                        # Proper track 'TITLE ' is detected
                        pos = pos1+6
                        pos1 = self.cuetext.find('\n', pos)
                        if pos1 < 0:
                            break
                        cueStr = cutCueLine(self.cuetext[pos:pos1])
                    else:
                        # Try entry 'FILE "##. Title.*" WAVE' when proper 'TITLE ' is missing
                        pos1 = self.cuetext.rfind('FILE "', 0, pos)
                        if pos1 < 0:
                            break
                        pos1 += 6
                        pos2 = self.cuetext.find('" WAVE', pos1)
                        if pos2 < 0:
                            break
                        # Extract number and title from file name
                        numAndTitle = self.cuetext[pos1:pos2]
                        namePos = 0
                        while namePos < len(numAndTitle) and numAndTitle[namePos].isdigit():
                            namePos += 1
                        # ~ print("ALB CUE ", numAndTitle, namePos)
                        if namePos < len(numAndTitle) and (numAndTitle[namePos] in ['.','-',' '] or namePos < len(numAndTitle)/3.0):
                            trackNo = numAndTitle[:namePos]
                            cueStr = numAndTitle[namePos:].lstrip()
                            if cueStr[0] == '.' or cueStr[0] == '-':
                                cueStr = cueStr[1:].lstrip()
                            # Cut extension if present
                            pos1 = cueStr.rfind('.')
                            if pos1 > 0:
                                cueStr = cueStr[:pos1].rstrip()
                            # Check if track number coincides with its index in 'TITLE '
                            if not (i+1 == tInd and tInd == int(trackNo)):
                                self.strStatus += f"\n\t+ suspicious track number '{tInd}' in cuesheet, expected '{i+1}'"
                        else:
                            self.name = numAndTitle
                    # Append cue title to the list of cue entries
                    trackTitle = coerceTitle(cueStr)
                    self.cueEntries.append(trackTitle)
                # Check the constructed list of cue entries
                if len(self.cueEntries) != self.trackTotal:
                    self.strStatus += f"\n\t+ failed to parse all {self.trackTotal} track entries from cuesheet '{self.cuesheet}'. Cuesheet incomplete?"

        # Revise artist, year, album title
        if 0 == len(self.artist) or 0 == self.year or 0 == len(self.title):
            lowName = self.dirName.lower()
            if lowName in ["misc", "miscellaneous", "various"]:
                # Somewhat special case of 'Misc' folder
                self.year = 0
                self.title = "Misc"
                self.name = "Misc"
            elif singleAlbum:
                # Single album mode
                parts = [p.strip() for p in self.dirName.split('-')]
                # Guess year if needed
                if 0 == self.year:
                    for i, p in enumerate(parts):
                        if p.isnumeric():
                            dirYear = int(p)
                            parts.remove(p)
                            if 0 < dirYear <= NOW_YEAR:
                                self.year = dirYear
                                self.strStatus += f"\n\t+ album year deduced from album dir name: {self.year:04d}"
                                break
                # Guess album name (and title prototype) if needed
                if 0 == len(self.title):
                    if len(parts) > 0:
                        self.name = parts[-1]
                        self.title = coerceTitle(self.name)
                        self.strStatus += f"\n\t+ album title deduced from album dir name: '{self.title}'"
                        parts.pop(-1)
                # Guess artist name if needed
                if 0 == len(self.artist):
                    if len(parts) > 0:
                        self.artist = parts[0]
                        self.strStatus += f"\n\t+ album artist deduced from album dir name: '{self.artist}'"
            else:
                # Album collection mode
                pos = self.dirName.find("-")
                if pos < 0:
                    if 0 == len(self.title):
                        self.name = self.dirName
                        self.title = coerceTitle(self.name)
                        self.strStatus += f"\n\t+ album title deduced from album dir name: '{self.title}'"
                else:
                    if 0 == self.year:
                        strYear = self.dirName[:pos].strip()
                        if strYear.isnumeric():
                            dirYear = int(strYear)
                            if 0 < dirYear <= NOW_YEAR:
                                self.year = dirYear
                                self.strStatus += f"\n\t+ album year deduced from album dir name: {self.year:04d}"
                    if 0 == len(self.title):
                        self.name = self.dirName[pos+1:].strip()
                        self.title = coerceTitle(self.name)
                        self.strStatus += f"\n\t+ album title deduced from album dir name: '{self.title}'"

        # Revise artist again
        if 0 == len(self.artist):
            rootArtist = os.path.basename(self.rootDir)
            if len(rootArtist) > 0:
                self.artist = rootArtist
                self.strStatus += f"\n\t+ artist name deduced from root dir name: '{self.artist}'"

        # Find cover image file
        self.cover = None
        for fName in albContents:
            if isImageFile(fName) and os.path.isfile(os.path.join(self.fullPath, fName)):
                img = CoverImage(self.fullPath, fName)
                if img.isNormal():
                    if self.cover == None:
                        self.cover = img
                    elif img > self.cover:
                        self.cover = img
        # Check the cover image
        if self.cover == None:
            self.strStatus += "\n\t+ cover image not found"
        else:
            self.strStatus += self.cover.strStatus

        # Count tracks manually if 'trackTotal' remains unclear
        if 0 == self.trackTotal:
            for fName in albContents:
                if isAudioFile(fName) and os.path.isfile(os.path.join(self.fullPath, fName)):
                    self.trackTotal += 1
        # Determine track number format
        strLastNum = str(self.trackTotal)
        self.tNumFmt = "0" + str(len(strLastNum)) + "d"

        # Build the collection of tracks
        trackFiles = []
        for fName in albContents:
            if isAudioFile(fName) and os.path.isfile(os.path.join(self.fullPath, fName)):
                trackFiles.append(fName)
        trackFiles.sort()   # Sort the tracks in alphabetical order

        # Instantiate tracks in alphabetical order
        self.tracks = []
        for trackIdx in range(len(trackFiles)):
            track = Track(self, trackFiles[trackIdx], 1+trackIdx)
            if track.isNormal():
                self.tracks.append(track)
        self.trackTotal = len(self.tracks)
        self.needsRecue |= (self.trackTotal != len(self.cueEntries))

        # The last try to improve album metadata
        albTitle = ""
        for track in self.tracks:
            if len(track.metaAlbum) > 0:
                albTitle = coerceTitle(track.metaAlbum)
                break
        if "Misc" != self.title:
            betterTitle = len(albTitle) >= len(self.title) and (self.title == ensureStringSafety(albTitle)) and (self.title != albTitle)
            if 0 == len(self.title) or betterTitle:
                self.title = albTitle
                self.name = ensureStringSafety(self.title)
                if 0 == len(self.title):
                    self.strStatus += "\n\t+ unknown album title"
                else:
                    self.strStatus += f"\n\t+ album title deduced from track metadata '{self.title}'"
        #
        albArtist = ""
        for track in self.tracks:
            if len(track.metaArtist) > 0:
                albArtist = track.metaArtist
                break
        betterArtist = len(albArtist) >= len(self.artist) and (self.artist == ensureStringSafety(albArtist)) and (self.artist != albArtist)
        if 0 == len(self.artist) or betterArtist:
            self.artist = albArtist
            if 0 == len(self.artist):
                self.strStatus += "\n\t+ unknown album artist"
            else:
                self.strStatus += f"\n\t+ album artist deduced from track metadata '{self.artist}'"
        #
        if allowComposer:
            albComposer = ""
            for track in self.tracks:
                if len(track.metaComposer) > 0:
                    albComposer = track.metaComposer
                    break
            betterComposer = len(albComposer) >= len(self.composer) and (self.composer == ensureStringSafety(albComposer)) and (self.composer != albComposer)
            if 0 == len(self.composer) or betterComposer:
                self.composer = albComposer
                if len(self.composer) > 0:
                    self.strStatus += f"\n\t+ album composer deduced from track metadata '{self.composer}'"
        #
        if 0 == self.year and "Misc" != self.title:
            for track in self.tracks:
                if track.metaDate > 0:
                    self.year = track.metaDate
                    break
            if 0 == self.year:
                self.strStatus += "\n\t+ unknown album year"
            else:
                self.strStatus += f"\n\t+ album year deduced from track metadata {self.year}"
        #
        if 0 == len(self.genre):
            for track in self.tracks:
                if len(track.metaGenre) > 0:
                    self.genre = track.metaGenre
                    break
            if 0 == len(self.genre):
                self.strStatus += "\n\t+ unknown album genre"
            else:
                self.strStatus += f"\n\t+ album genre deduced from track metadata '{self.genre}'"

        # Suggest perfect dir name
        if self.year > 0:
            self.goodName = f"{self.year:04d} - {self.name}"
        else:
            self.goodName = self.name
        if singleAlbum and len(self.composer) + len(self.artist) > 0 and "Misc" != self.title:
            if allowComposer and len(self.composer) > 0:
                self.goodName = ensureStringSafety(self.composer) + " - " + self.goodName
            else:
                self.goodName = ensureStringSafety(self.artist) + " - " + self.goodName
        if self.goodName != self.dirName:
            self.strStatus += f"\n\t+ imperfect dir name format, suggested '{self.goodName}'"
            self.needsRename = True

        # When no cue enties were parsed
        if len(self.cueEntries) == 0:
            self.strStatus += "\n\t! Only positive updates of track metadata might take place since cuesheet data is limited"
        if self.needsRecue:
            self.strStatus += "\n\t! Cuesheet will be reconstructed from track names and metadata"

        # Check the tracks
        self.tracks.sort(key = lambda track: track.number)
        self.tracksOk = True
        for track in self.tracks:
            self.tracksOk &= track.isOk()
            self.strStatus += track.strStatus

    def isOk(self):
        self.allOk = len(self.name) > 0 and not self.needsRename and not self.needsRecue \
                and len(self.cuetext) > 0 and not self.manyCues \
                and self.trackTotal > 0 and self.tracksOk \
                and self.cover != None and self.cover.isOk()
        return self.allOk

    def hasSmthToDo(self):
        if self.allOk:
            return False
        else:
            return self.needsRename or (not self.tracksOk) \
                    or (self.cover != None and not self.cover.isOk()) \
                    or (self.needsRecue and len(self.tracks) > 0)

    def __str__(self):
        if self.allOk:
            return f"Flat Album '{self.title}' STATUS: OK {self.strStatus}"
        else:
            return f"Flat Album '{self.title}' STATUS: SOME PROBLEMS {self.strStatus}"

    def coerce(self):
        print(f"Coercing flat album '{self.goodName}'", end="")
        if self.allOk:
            print(" OK, SKIPPED")
            return
        else:
            print(":")

        if self.cover != None:
            self.cover.coerce()

        for track in self.tracks:
            track.coerce()

        # Update replay gain if needed
        flacTracks = []
        mp3Tracks = []
        for track in self.tracks:
            if track.needsReplayGain:
                if "flac" == track.codec:
                    flacTracks.append(track.fullPath)
                elif "mp3" == track.codec:
                    mp3Tracks.append(track.fullPath)
        if len(flacTracks) > 0:
            print("\t* Updating FLAC replay gain information:", end=' ')
            res, err = proc.Popen(['metaflac', '--dont-use-padding', '--add-replay-gain'] + flacTracks, stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
            if len(err) == 0:
                print("DONE")
            else:
                print("\nERROR when adding replay gain into FLAC tracks, metaflac's report reads:\n"+err)
        if len(mp3Tracks) > 0:
            print("\t* Updating MP3 replay gain information:", end=' ')
            res, err = proc.Popen(['mp3gain', '-r', '-q', '-c', '-t'] + mp3Tracks, stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
            if len(err) == 0:
                print("DONE")
            else:
                print("\nERROR when adding replay gain into MP# tracks, mp3gain's report reads:\n"+err)

        if self.needsRename:
            newFullPath = os.path.join(self.rootDir, self.goodName)
            os.rename(self.fullPath, newFullPath)
            self.fullPath = newFullPath
            print(f"\t* Coercing album name to '{self.goodName}': DONE")

        # Update track status after coercing
        self.tracksOk = True
        for track in self.tracks:
            track.albumPath = self.fullPath
            track.fullPath = os.path.join(track.albumPath, track.audioFile)
            self.tracksOk &= track.isOk()

        # Generate cuesheet if missing or broken
        if self.needsRecue and len(self.tracks) > 0:
            self.cuesheet = self.goodName+".cue"
            print(f"\t* Reconstructing cuesheet '{self.cuesheet}':", end=' ')
            if len(self.title) > 0:
                self.cuetext  = f'TITLE "{self.title}"\n'
            if len(self.artist) > 0:
                self.cuetext += f'PERFORMER "{self.artist}"\n'
            if allowComposer and len(self.composer) > 0:
                self.cuetext += f'REM COMPOSER "{self.composer}"\n'
            if self.year > 0:
                self.cuetext += f'REM DATE {self.year}\n'
            if len(self.genre) > 0:
                self.cuetext += f'REM GENRE "{self.genre}"\n'
            self.cuetext += f'FILE "{self.goodName}.flac" WAVE\n'
            index = 0.0
            for track in self.tracks:   # Loop through all the tracks
                self.cuetext += f'  TRACK {track.metaNumber:{self.tNumFmt}} AUDIO\n'
                self.cuetext += f'    TITLE "{track.metaTitle}"\n'
                idxMin = int(index/60.0)
                idxSec = int(index - 60*idxMin)
                idxMs  = int(100*(index - int(index)))
                self.cuetext += f'    INDEX 01 "{idxMin:02d}:{idxSec:02d}:{idxMs:02d}"\n'
                strDurSec = os.popen(f'ffprobe -v error -select_streams a:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 "{track.fullPath}"').read()
                try:
                    index += float(strDurSec)
                except Exception:
                    pass
            # Write the reconstructed cuesheet
            cuePath = os.path.join(self.fullPath, self.cuesheet)
            fCue = open(cuePath, "w")
            fCue.write(self.cuetext)
            fCue.close()
            durMin = int(index/60.0)
            durSec = index - durMin*60
            durHrs = int(durMin/60.0)
            strDur = ""
            if durHrs > 0:
                durMin -= durHrs * 60
                strDur = str(durHrs) + " hr"
                if durHrs % 10 != 1:
                    strDur += "s"
                strDur += " "
            print(f"duration {strDur}{durMin} min {durSec:.2f} sec DONE")

class UnflatAlbum:

    def __init__(self, fullAlbumPath):
        # Define class fields
        self.fullPath = ""
        self.rootDir = ""
        self.dirName = ""
        self.goodName = ""
        #
        self.artist = ""
        self.composer = ""
        self.title = ""
        self.year = 0
        self.genre = ""
        self.name = ""
        #
        self.commPref = ""
        self.commPost = ""
        #
        self.numCues = 0
        self.cueList = []
        self.cueTrackTitles = []
        self.cueTrackTotals = []
        self.cueIndexes = []
        self.tNumFmt = ""
        #
        self.subAlbums = []
        self.subCounts = []
        self.allSubElems = []
        #
        self.strStatus = ""
        self.needsRename = False

        # Common album setup
        self.fullPath = fullAlbumPath
        self.dirName = os.path.basename(self.fullPath)
        self.rootDir = os.path.dirname(self.fullPath)

        # Check defined metadata
        if len(albumTitle) > 0:
            self.title = albumTitle
            self.name = ensureStringSafety(self.title)
        if len(bandName) > 0:
            self.artist = bandName
        if allowComposer and len(composerName) > 0:
            self.composer = composerName
        if albumYear != 0:
            self.year = albumYear
        if len(albumGenre) > 0:
            self.genre = albumGenre

        # Find sub-albums
        contents = os.listdir(self.fullPath)
        self.subAlbums = []
        self.subCounts = []
        self.allSubElems = []
        self.cueList = []
        self.cueTrackTotals = []        # Count right now (from track files)
        self.cueTrackTitles = []        # Construct right now (from track filenames)
        for elem in contents:
            fullElem = os.path.join(self.fullPath, elem)
            if canBeAlbum(fullElem, insideComplex=True):
                self.subAlbums.append(elem)
                #
                subElems = os.listdir(fullElem)
                self.allSubElems += subElems
                self.subCounts.append(len(subElems))
                #
                localTracks = []
                for s in subElems:
                    if isAudioFile(s):
                        lastDot = s.rfind(".")
                        newName = coerceTitle(s[:lastDot].strip())
                        nameLen = len(newName)
                        for i in range(nameLen):
                            if not newName[i].isdigit():
                                if i <= nameLen/2:
                                    newName = newName[i:].strip()
                                    if newName[0] in ['.', '-']:
                                        newName = newName[1:].strip()
                                break
                        localTracks.append(newName)
                self.cueTrackTitles.append(localTracks)
                self.cueTrackTotals.append(len(localTracks))
                #
                localCues = [os.path.join(fullElem,s) for s in subElems if s.lower().endswith(".cue")]
                if 0 == len(localCues):
                    continue
                bestCue = localCues[0]
                bestSize = os.path.getsize(bestCue)
                if len(localCues) > 1:
                    for cue in localCues[1:]:
                        cueSize = os.path.getsize(cue)
                        if cueSize > bestSize:
                            bestCue = cue
                            bestSize = cueSize
                    self.strStatus += f"\n\t+ multiple cuesheets in sub-album '{elem}', suggested '{bestCue}' (size {int(bestSize/1024)} KiB)"
                self.cueList.append(bestCue)
        self.numCues = len(self.cueList)
        # Sort sub-albums
        self.subAlbums.sort()
        self.cueList.sort()

        # Find common prefixes
        self.commPref, self.commPost = getCommonPrefPostFixes(self.subAlbums)

        # Get information either from cuesheets
        if self.numCues > 0:
            # Extract data from cuesheets
            cueArtists = [] # Later: Check for same and with self.artist (may be defined)
            cueComposers =[]# Later: Check for same and with self.composer (may be defined)
            cueTitles = []  # Later: Check for similar (common pre/postfix) and with self.title (may be defined)
            cueYears = []   # Later: Check for same and with self.year (may be defined)
            cueGenres = []  # Later: Unite
            self.cueTrackTotals = []    # Count right now
            self.cueTrackTitles = []    # Construct right now
            self.cueIndexes = []        # Construct right now
            for cueFile in self.cueList:
                cuetext = loadAndForceUTF8(cueFile)
                shortCuePath = os.path.relpath(cueFile, self.fullPath)
                if len(cuetext) == 0:
                    self.strStatus += f"\n\t+ cuesheet file '{shortCuePath}' is empty"
                else:
                    # Check album title from cuesheet
                    pos = cuetext.find('TITLE ')
                    if pos >= 0:
                        end = cuetext.index('\n', pos+6)
                        cueStr = cutCueLine(cuetext[pos+6:end])
                        if len(cueStr) > 0:
                            cueTitles.append(coerceTitle(cueStr))

                    # Check year from cuesheet
                    pos = cuetext.find('REM DATE ')
                    if pos >= 0:
                        end = cuetext.index('\n', pos+9)
                        cueStr = cutCueLine(cuetext[pos+9:end])
                        if cueStr.isnumeric():
                            cueYear = int(cueStr)
                            if cueYear > 0 and cueYear <= NOW_YEAR:
                                cueYears.append(cueYear)

                    # Extract genre from cuesheet
                    pos = cuetext.find('REM GENRE ')
                    if pos >= 0:
                        end = cuetext.index('\n', pos+10)
                        cueStr = cutCueLine(cuetext[pos+10:end])
                        if len(cueStr) > 0:
                            cueGenres.append(cueStr)

                    # Extract artist from cuesheet
                    pos = cuetext.find('PERFORMER ')
                    if pos >= 0:
                        end = cuetext.index('\n', pos+10)
                        cueStr = cutCueLine(cuetext[pos+10:end])
                        if len(cueStr) > 0:
                            cueArtists.append(cueStr)

                    # Extract composer from cuesheet
                    if allowComposer:
                        pos = cuetext.find('COMPOSER ')
                        if pos >= 0:
                            end = cuetext.index('\n', pos+9)
                            cueStr = cutCueLine(cuetext[pos+9:end])
                            if len(cueStr) > 0:
                                cueComposers.append(cueStr)

                    # Extract tracktotal from cuesheet
                    cueTrackTotal = 0
                    trackTotalPos = cuetext.rfind('TRACK ')
                    if trackTotalPos < 0:
                        self.strStatus += f"\n\t+ missing TRACKs in cuesheet '{shortCuePath}', please add some"
                    else:
                        end = cuetext.index(' ', trackTotalPos+6)
                        trackTot = cuetext[trackTotalPos+6:end].strip()
                        if not trackTot.isnumeric():
                            self.strStatus += f"\n\t+ invalid chars '{trackTot}' after the last TRACK in cuesheet '{shortCuePath}'"
                        else:
                            cueTrackTotal = int(trackTot)
                            if cueTrackTotal < 1 or cueTrackTotal > MAX_TRACKS:
                                self.strStatus += f"\n\t+ unsupported track number {cueTrackTotal} in cuesheet '{shortCuePath}'"

                    # Build the list of track entries and indexes from this cuesheet
                    pos = 0
                    cueEntries = []
                    cueEntIdxes = []
                    # print("COMPL ALB CUE ",cueTrackTotal)
                    for i in range(cueTrackTotal):
                        # Find the next track
                        pos1 = cuetext.find('TRACK ', pos)
                        if pos1 < 0:
                            break
                        pos = pos1+6
                        end = cuetext.find(' ', pos)
                        # Find track number
                        trackNo = cuetext[pos:end].strip()
                        # print("COMPL ALB CUE ",pos1,end,trackNo)
                        if trackNo.isnumeric():
                            tInd = int(trackNo)
                            if i+1 != tInd:
                                self.strStatus += f"\n\t+ suspicious track number '{tInd}' in cuesheet, expected '{i+1}'"
                        else:
                            break
                        # Find track title
                        pos1Orig = pos1
                        pos1 = cuetext.find('TITLE ', pos) # Position of track title
                        pos2 = cuetext.find('TRACK ', pos) # Position of the next track
                        # print("COMPL ALB CUE ",pos1,pos2)
                        if pos2 < 0:
                            pos2 = len(cuetext)
                        if pos1 > 0 and pos1 < pos2:
                            # Proper track 'TITLE ' is detected
                            pos = pos1+6
                            pos1 = cuetext.find('\n', pos)
                            if pos1 < 0:
                                break
                            cueStr = cutCueLine(cuetext[pos:pos1])
                        else:
                            # Try entry 'FILE "##. Title.*" WAVE' when proper 'TITLE ' is missing
                            pos1 = cuetext.rfind('FILE "', 0, pos)
                            if pos1 < 0:
                                break
                            pos1 += 6
                            pos2 = cuetext.find('" WAVE', pos1)
                            if pos2 < 0:
                                break
                            # Extract number and title from file name
                            numAndTitle = cuetext[pos1:pos2]
                            namePos = 0
                            while namePos < len(numAndTitle) and numAndTitle[namePos].isdigit():
                                namePos += 1
                            # ~ print("COMPL ALB CUE ", numAndTitle, namePos)
                            if namePos < len(numAndTitle) and (numAndTitle[namePos] in ['.','-',' '] or namePos < len(numAndTitle)/3.0):
                                trackNo = numAndTitle[:namePos]
                                cueStr = numAndTitle[namePos:].lstrip()
                                if cueStr[0] == '.' or cueStr[0] == '-':
                                    cueStr = cueStr[1:].lstrip()
                                # Cut extension if present
                                pos1 = cueStr.rfind('.')
                                if pos1 > 0:
                                    cueStr = cueStr[:pos1].rstrip()
                                # Check if track number coincides with its index in 'TITLE '
                                if not (i+1 == tInd and tInd == int(trackNo)):
                                    self.strStatus += f"\n\t+ suspicious track number '{tInd}' in cuesheet, expected '{i+1}'"
                            else:
                                self.name = numAndTitle
                            # Restore 'pos1' to the current 'TRACK ##'
                            pos1 = pos1Orig
                        # Append cue title to the list of cue entries
                        trackTitle = coerceTitle(cueStr)
                        cueEntries.append(trackTitle)
                        pos = pos1+1
                        # Find track indexes
                        posNext = cuetext.find('TRACK ', pos)
                        if posNext < 0:
                            posNext = len(cuetext)  # We are working with the last track, so limit it due to file end
                        entIdxes = []
                        pos1 = cuetext.find('INDEX 00 ', pos)
                        if pos1 > 0 and pos1 < posNext:
                            end = cuetext.find('\n', pos1+9)
                            if end > pos1:
                                cueIdx = cuetext[pos1+9:end].lstrip()
                                if '\r' == cueIdx[-1]:
                                    cueIdx = cueIdx[:-1].rstrip()
                                entIdxes.append(cueIdx)
                        pos1 = cuetext.find('INDEX 01 ', pos)
                        if pos1 > 0 and pos1 < posNext:
                            end = cuetext.find('\n', pos1+9)
                            if end > pos1:
                                cueIdx = cuetext[pos1+9:end].lstrip()
                                if '\r' == cueIdx[-1]:
                                    cueIdx = cueIdx[:-1].rstrip()
                                entIdxes.append(cueIdx)
                        if 0 == len(entIdxes):
                            cueEntIdxes.append(["00:00:00"])
                        else:
                            cueEntIdxes.append(entIdxes)

                    # Check the list of cue entries
                    if len(cueEntries) != cueTrackTotal:
                        self.strStatus += f"\n\t+ failed to parse all {cueTrackTotal} track entries from cuesheet '{shortCuePath}'. Cuesheet incomplete?"
                    self.cueTrackTotals.append(len(cueEntries))
                    self.cueTrackTitles.append(cueEntries)
                    self.cueIndexes.append(cueEntIdxes)
            # Analyze data collected from cuesheets
            # Check artists
            if 0 == len(self.artist):
                cueArtists = list(set(cueArtists))  # Remove duplicate artists if any
                if 0 == len(cueArtists):
                    self.strStatus += f"\n\t+ missing PERFORMER tag in every cuesheet under '{self.dirName}'"
                elif 1 == len(cueArtists):
                    self.artist = cueArtists[0]
                else:
                    self.artist = ""
                    for artist in cueArtists:
                        if len(artist) > len(self.artist):
                            self.artist = artist
                    self.strStatus += f"\n\t+ multiple PERFORMER in cuesheets, suggested '{self.artist}'"
            # Check composers
            if 0 == len(self.composer):
                cueComposers = list(set(cueComposers))  # Remove duplicate composers if any
                # ~ if 0 == len(cueComposers):
                    # ~ self.strStatus += f"\n\t+ missing REM COMPOSER tag in every cuesheet under '{self.dirName}'"
                if 1 == len(cueComposers):
                    self.composer = cueComposers[0]
                elif len(cueComposers) > 1:
                    self.composer = ""
                    for composer in cueComposers:
                        if len(composer) > len(self.composer):
                            self.composer = composer
                    self.strStatus += f"\n\t+ multiple REM COMPOSER in cuesheets, suggested '{self.composer}'"
            # Check titles
            if 0 == len(self.title):
                if 0 == len(cueTitles):
                    self.strStatus += f"\n\t+ missing TITLE \"...\" tag in every cuesheet under '{self.dirName}'"
                else:
                    pref, post = getCommonPrefPostFixes(cueTitles)
                    if len(pref) > 0:
                        self.title = coerceTitle(pref.strip())
                    elif len(post) > 0:
                        self.title = coerceTitle(post.strip())
                    else:
                        self.title = cueTitles[0]
                        for title in cueTitles[1:]:
                            if len(title) > len(self.title):
                                self.title = title
                        self.strStatus += f"\n\t too different album TITLEs in cuesheets, suggested '{self.title}'"
                    delStr = self.commPref + self.commPost  # Only one of them may be non-empty
                    # Remove common pre/postfix if detected
                    if len(delStr) > 0:
                        if self.title.endswith(delStr):
                            self.title = self.title[:-len(delStr)].rstrip()
                            if not self.title[-1].isalpha():
                                self.title = self.title[:-1].rstrip()
                        elif self.title.startswith(delStr):
                            self.title = self.title[len(delStr):].lstrip()
                            if not self.title[0].isalpha():
                                self.title = self.title[1:].lstrip()
                    self.name = ensureStringSafety(self.title)
            # Check years
            if 0 == self.year:
                if 0 == len(cueYears):
                    self.strStatus += f"\n\t+ missing REM DATE tag in every cuesheet under '{self.dirName}'"
                else:
                    meanYear = sum(cueYears) / len(cueYears)
                    self.year = round(meanYear)
                    self.strStatus += f"\n\t+ album year deduced from cuesheets: {self.year}"
            # Check genres
            if 0 == len(self.genre):
                if 0 == len(cueGenres):
                    self.strStatus += f"\n\t+ missing REM GENRE tag in every cuesheet under '{self.dirName}'"
                else:
                    allGenres = []
                    for grs in cueGenres:
                        genres = [g.strip().title() for g in grs.split(',')]
                        allGenres += genres # Collect all genres
                    allGenres = list(set(allGenres))    # Remove duplicate genres
                    self.genre = ', '.join(allGenres)

        # Revies
        trackTotal = sum(self.cueTrackTotals)
        self.tNumFmt = f"0{len(str(trackTotal))}d"

        # Revise year and album title
        if 0 == len(self.title) or 0 == self.year:
            # Guess year and album name (and title prototype) from dir name if they are undefined
            firstDashPos = self.dirName.find('-')
            if firstDashPos < 0:
                if 0 == len(self.title):
                    self.title = coerceTitle(self.dirName.strip())
                    self.name = ensureStringSafety(self.title)  # Title prototype, will be likely improved later
                    self.strStatus += f"\n\t+ album title deduced from album dir name: '{self.title}'"
            else:
                txtDate = self.dirName[:firstDashPos].strip()
                if txtDate.isnumeric() and 0 == self.year:
                    self.year = int(txtDate)
                    if self.year < 0 or self.year > NOW_YEAR:
                        self.year = 0
                    else:
                        self.strStatus += f"\n\t+ album year deduced from album dir name: '{self.year}'"
                folderName = self.dirName[firstDashPos+1:].strip()
                if 0 == len(self.title):
                    self.title = coerceTitle(folderName)    # Title prototype, will be likely improved later
                    self.name = ensureStringSafety(self.title)
                    self.strStatus += f"\n\t+ album title deduced from album dir name: '{self.title}'"
        if 0 == len(self.title):
            self.strStatus += "\n\t+ unknown album title"
        if 0 == self.year:
            self.strStatus += "\n\t+ unknown album year"

        # Revise artist
        if 0 == len(self.artist):
            self.artist = os.path.basename(self.rootDir)
            self.strStatus += f"\n\t+ artist name deduced from root dir name: '{self.artist}'"

        # Suggest perfect dir name
        if self.year > 0:
            self.goodName = f"{self.year:04d} - {self.name}"
        else:
            self.goodName = self.name
        if singleAlbum and len(self.composer) + len(self.artist) > 0:
            if allowComposer and len(self.composer) > 0:
                self.goodName = ensureStringSafety(self.composer) + " - " + self.goodName
            else:
                self.goodName = ensureStringSafety(self.artist) + " - " + self.goodName
        if self.goodName != self.dirName:
            self.strStatus += f"\n\t+ imperfect dir name format, suggested '{self.goodName}'"
            self.needsRename = True

    def isNormal(self):
        return len(self.subAlbums) > 0 and (len(self.commPref) > 0 or len(self.commPost) > 0) \
                and len(self.allSubElems) > len(self.subAlbums)

    def __str__(self):
        numSubs = len(self.subAlbums)
        toStr = f"Complex Album '{self.title}' with {numSubs} sub-albums (total {len(self.allSubElems)} elements):"
        for i in range(numSubs):
            toStr += f"\n\t* '{self.subAlbums[i]}' with {self.subCounts[i]} elements ({self.cueTrackTotals[i]} tracks)"
        toStr += f"\n\t+ common prefix '{self.commPref}', common postfix '{self.commPost}'"
        toStr += f"\n\t+ {self.numCues} cuesheets will be merged"
        toStr += self.strStatus
        toStr += f"\n\t= '{self.goodName}' by '{self.artist}', style: '{self.genre}'"
        return toStr

    def coerce(self):
        print(f"Flattening the complex album '{self.goodName}' (dir name '{self.dirName}')")
        # Flatten the album
        baseIndex = 0
        for i in range(len(self.subAlbums)):
            subAlbum = self.subAlbums[i]
            subAlbumPath = os.path.join(self.fullPath, subAlbum)
            subElements = os.listdir(subAlbumPath)
            for subElem in subElements:
                newName = subElem
                # Find filename extension
                newExt = ""
                dotPos = newName.rfind('.')
                if dotPos > 0:
                    newExt = newName[dotPos:].lower()   # Force lowercase extension right away
                    newName = newName[:dotPos].rstrip()
                # Check element uniqueness
                if self.allSubElems.count(subElem) > 1:
                    newName += " ("+subAlbum+")"
                # Find file index (for numbered files only)
                newNumStr = ""
                for j in range(len(newName)):
                    if newName[j].isdigit():
                        newNumStr += newName[j]
                    else:
                        newName = newName[j:]
                        break
                # Shift file index if it exists
                numLen = len(newNumStr)
                if numLen > 0:
                    idx = int(newNumStr)
                    idx += baseIndex
                    newNumStr = f"{idx:{self.tNumFmt}}" # Convert shifted index to a string looking similar to the old one
                # Reconstruct updated name and move the element into parent dir
                if ".cue" == newExt:
                    newExt = ".cdcue"   # Rename old cuesheets so that they do not interfere with a newly generated one
                newElem = newNumStr + newName + newExt
                oldPath = os.path.join(subAlbumPath, subElem)
                newPath = os.path.join(self.fullPath, newElem)
                os.rename(oldPath, newPath)

            # Increase base index by the bulk amount of elements in previous sub-folder
            baseIndex += self.cueTrackTotals[i]
            # Delete the old (now empty) folder
            os.rmdir(subAlbumPath)
            print(f"\t* sub-album '{subAlbum}' ({self.cueTrackTotals[i]} tracks) flattened")

        # Reconstruct unified cuesheet
        if len(self.title) > 0:
            cuetext  = f'TITLE "{self.title}"\n'
        if len(self.artist) > 0:
            cuetext += f'PERFORMER "{self.artist}"\n'
        if allowComposer and len(self.composer) > 0:
            cuetext += f'REM COMPOSER "{self.composer}"\n'
        if self.year > 0:
            cuetext += f'REM DATE {self.year}\n'
        if len(self.genre) > 0:
            cuetext += f'REM GENRE "{self.genre}"\n'
        baseIndex = 1
        for i in range(len(self.subAlbums)):        # Loop through sub-albums
            cuetext += f'FILE "{self.goodName} ({self.subAlbums[i]}).flac" WAVE\n'
            for j in range(self.cueTrackTotals[i]): # Loop through tracks in the i-th sub-album
                cuetext += f'  TRACK {baseIndex+j:{self.tNumFmt}} AUDIO\n'
                cuetext += f'    TITLE "{self.cueTrackTitles[i][j]}"\n'
                if len(self.cueIndexes) > 0:
                    cuetext += f'    INDEX 00 "{self.cueIndexes[i][j][0]}"\n'
                    if 2 == len(self.cueIndexes[i][j]):
                        cuetext += f'    INDEX 01 "{self.cueIndexes[i][j][1]}"\n'
            baseIndex += self.cueTrackTotals[i]
        # Write the unified cuesheet
        cueFile = os.path.join(self.fullPath, self.goodName+".cue")
        fCue = open(cueFile, "w")
        fCue.write(cuetext)
        fCue.close()
        print(f"\t* unified cuesheet '{self.goodName}.cue' written")

        # Rename the whole directory if needed
        if self.needsRename:
            oldPath = self.fullPath
            newPath = os.path.join(self.rootDir, self.goodName)
            os.rename(oldPath, newPath)
            print(f"\t* album renamed into '{self.goodName}'")


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# Main execution starts here
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---


# 0. Check environment capabilities: 'file', 'ffmpeg', 'ffprobe', 'magick', 'identify', 'metaflac', 'mid3v2' and 'mutagen-inspect' programs
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
PROG_LIST = ['file', 'ffmpeg', 'ffprobe', 'magick', 'identify', 'metaflac', 'mid3v2', 'mutagen-inspect', 'mp3gain']
progsOk = True
for progName in PROG_LIST:
    resp = proc.Popen(['which', progName], stdout=proc.PIPE, stderr=proc.STDOUT, text=True).communicate()[0]
    if '\n' == resp[-1]:
        resp = resp[:-1]
    if not os.path.isfile(resp):
        print("* Please, install '"+progName+"'")
        progsOk = False
if not progsOk:
    print("FATAL: operation impossible without aforementioned utilities")
    print("For ArchLinux system take a look at 'ffmpeg', 'imagemagick', 'flac', 'python-mutagen' and 'mp3gain' packages")
    sys.exit(-1)


# I. Get main directory (band name) and determine whether dry run is under way
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
print = functools.partial(print, flush=True)
if (len(sys.argv) < 1+1):
    print("Please, provide path to base directory")
    sys.exit()

# Parse base directory
if "--help" == sys.argv[1]:
    ShowHelp()
    sys.exit(0)
baseDir = sys.argv[1]
if (not os.path.isdir(baseDir)):
    print("Directory '"+baseDir+"' is inaccessible")
    sys.exit()
baseDir = os.path.abspath(baseDir)

# Parse other arguments
dryRun = True
noCaps = False
skipReplayGain = False
singleAlbum = False
allowComposer = False
minTracks = 3
bandName = ""
composerName = ""
albumTitle = ""
albumYear = 0
albumGenre = ""
for arg in sys.argv[2:]:
    if arg.startswith("--artist="):
        bandName = arg[9:]
    elif arg.startswith("--composer="):
        composerName = arg[11:]
        allowComposer = True
    elif arg.startswith("--year="):
        albumYear = int(arg[7:])
    elif arg.startswith("--album="):
        albumTitle = arg[8:]
    elif arg.startswith("--genre="):
        albumGenre = arg[8:]
    elif arg.startswith("--min-tracks="):
        try:
            minTracks = int(arg[13:])
        except:
            print("FATAL: failed to parse the '"+arg+"' option")
            sys.exit(0)
    elif arg == "--coerce":
        dryRun = False
    elif arg == "--no-cap":
        noCaps = True
    elif arg == "--skip-replaygain":
        skipReplayGain = True
    elif arg == "--single-album":
        singleAlbum = True
    elif arg == "--unify-composer":
        allowComposer = True
    elif arg == "--help":
        ShowHelp()
        sys.exit(0)
    else:
        print("Invalid argument '"+arg+"', pass '--help' to get more information")
        sys.exit(-1)

# Ensure that user knows what a 'perfect' title actually is :)
if len(albumTitle) > 0:
    if not singleAlbum:
        print("WARNING: --album='...' can only be used together with '--single-album' option")
        sys.exit(0)
    perfTitle = coerceTitle(albumTitle)
    if albumTitle != perfTitle:
        print(f"Supplied title '{albumTitle}' is imperfect, please, pass '{perfTitle}'")
        sys.exit(-1)

# Report global settings
print(" ==="*20)
print(f"Working with directory '{baseDir}'")
if singleAlbum:
    print("MODE: Single album")
else:
    print("MODE: Album collection")
if len(bandName) > 0:
    print(f"Defined artist is '{bandName}'")
else:
    print("Artist will be deduced")
if len(composerName) > 0:
    print(f"Defined composer is '{composerName}'")
if len(albumGenre) > 0:
    print(f"Defined genre is '{albumGenre}'")
else:
    print("Genre will be deduced")
if len(albumTitle) > 0:
    print(f"Defined album is '{albumTitle}'")
else:
    if singleAlbum:
        print("Album title will be deduced")
    else:
        print("Miscellaneous albums")
if 0 == albumYear:
    if singleAlbum:
        print("Album year will be deduced")
    else:
        print("Miscellaneous years")
elif 0 < albumYear:
    print(f"Defined album year is {albumYear}")
else:
    print("Preserving year metadata")
if dryRun:
    print("DRY RUN - nothing will be changed")
else:
    ch = input("WARNING: COERCIVE MODE REQUESTED! Continue? (y/n): ")
    dryRun = ('y' != ch)
    if not dryRun:
        print("THERE IS NO COMING BACK NOW")
    else:
        print("ABORTED")
        sys.exit()
print() # Clear line


# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---


albums = []
numAlbums = 0
unflatAlbums = []
numUnflatAlbums = 0
everythingOk = True
hasSmthToDo = False

if not singleAlbum:
    # II.a. Find subdirectories -- albums (in collection mode)
    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
    if not os.path.isdir(baseDir):
        print(f"ERROR: Given directory '{baseDir}' is unlikely to be a collection of albums")
        sys.exit()
    #
    for entry in os.listdir(baseDir):
        fullEntry = os.path.join(baseDir, entry)
        if canBeAlbum(fullEntry):
            numAlbums += 1
            album = Album(fullEntry)
            albums.append(album)
            everythingOk &= album.isOk()
            hasSmthToDo |= album.hasSmthToDo()
            print(f"{numAlbums+numUnflatAlbums:3d}. {album}")
        elif canBeComplexAlbum(fullEntry):
            album = UnflatAlbum(fullEntry)
            if album.isNormal():
                unflatAlbums.append(album)
                numUnflatAlbums += 1
                everythingOk = False
                hasSmthToDo = True
                print(f"{numAlbums+numUnflatAlbums:3d}. {album}")
    # Sort albums
    albums.sort(key = lambda alb: alb.goodName)
    unflatAlbums.sort(key = lambda alb: alb.goodName)

else:
    # II.b. Find tracks or sub-albums (in single album mode)
    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
    if canBeAlbum(baseDir):
        album = Album(baseDir)
        albums = [album]
        numAlbums = 1
        everythingOk = album.isOk()
        hasSmthToDo = album.hasSmthToDo()
        print(album)
    elif canBeComplexAlbum(baseDir):
        album = UnflatAlbum(baseDir)
        if album.isNormal():
            unflatAlbums = [album]
            numUnflatAlbums = 1
            everythingOk = False
            hasSmthToDo = True
            print(album)
    else:
        print(f"ERROR: Given directory '{baseDir}' is unlikely to be an album")
        sys.exit()


# III. Coerce existing albums if needed
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
print('\n'+" ---"*20)
if singleAlbum:
    strClass = "Flat"
    if 1 == numUnflatAlbums:
        strClass = "Complex"
    print("Given album is classified as '"+strClass+"':", end=' ')
else:
    print(f"Found {numAlbums} flat albums, {numUnflatAlbums} complex albums:", end=' ')
if everythingOk:
    print("ALL OK")
    print(" ---"*20)
    sys.exit()
else:
    if hasSmthToDo:
        print("SOME SOLVABLE PROBLEMS")
        print(" ---"*20+'\n')
    else:
        print("SOME CRITICAL PROBLEMS, MANUAL INTERVENTION REQUIRED")
        print(" ---"*20+'\n')
        sys.exit()
    # Coercing
    if not dryRun and hasSmthToDo:
        nAlb = len(albums)
        for i, album in enumerate(albums):
            print(f"[{i+1:02d} / {nAlb:02d}] ", end='')
            album.coerce()
        nAlb = len(unflatAlbums)
        for i, album in enumerate(unflatAlbums):
            print(f"[{i+1:02d} / {nAlb:02d}] ", end='')
            album.coerce()
        print('\nFINISHED\n'+" ---"*20)
        sys.exit()
