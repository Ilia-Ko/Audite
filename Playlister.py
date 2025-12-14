#!/usr/bin/python

def PrintHelp():
    print(
"""
 The Playlister.py script helps to maintain coherence between link-based and m3u-based playlists.

 There are 3 usage scenarios:
  1. [links-to-m3u] Transfer a 'folder with links' playlist into an 'm3u' playlist
  2. [m3u-to-links] Expand an 'm3u' playlist into a 'folder with links'
  3. [inspect-list] Scan a 'folder with links' or 'm3u' playlist and convert/sort its entries nicely
  In both scenarious playlists are never truncated, only extended or left as is (if equivalent)

 1st scenario [links-to-m3u]:
  python Playlister.py --l2m "path/to/folder/with/links/" "path/to/playlist.m3u" "path/to/base/dir/" "alias-for-base-dir:"
   ARG1:   --l2m   activates the [links-to-m3u] regime
   ARG2:   "path/to/folder/with/links/"     specifies an input folder to scan for the links
   ARG3:   "path/to/playlist.m3u"   specifies path to the output playlist to be appended (or created if does not exist)
   ARG4:   "path/to/base/dir/"      specifies path to the local base directory to which all the links will be related
   ARG5:   "alias-for-base-dir:"    specifies a rename for the base directory (i.e. the name of corresponding base dir on an external device)
   ARG6:   "--sort-m3u"             whether to sort playlist file afterwards

 2nd scenario [m3u-to-links]:
  python Playlister.py --m2l "path/to/playlist.m3u" "path/to/folder/with/links/" "alias-for-base-dir:" "path/to/base/dir/"
   ARG1:   --m2l   activates the [m3u-to-links] regime
   ARG2:   "path/to/playlist.m3u"   specifies path to the input playlist to be expanded
   ARG3:   "path/to/folder/with/links/"     specifies an output folder to append the links at (will be created if does not exist)
   ARG4:   "alias-for-base-dir:"    specifies the name of a base directory on an external device
   ARG5:   "path/to/base/dir/"      specifies path to the local base directory to which all the links will be related
   ARG6:   "--full-links"           whether to construct link names in form 'Artist ∕ Year ∕ Album ∕ ##. Track'

 3rd scenario [inspect-list]:
  python Playlister.py --inspect "/path/to/folder/with/links/"      # Convert every link into relative ones and rename as 'Band ∕ Album ∕ ##. Track'
  python Playlister.py --inspect "/path/to/playlist.m3u"            # Sort playlist entries alphabetically
""")

import os
import sys
import subprocess as proc
import functools
import random as rnd

print = functools.partial(print, flush=True)
rnd.seed()

# Check environment capabilities: 'sort' and 'ln' programs
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
PROG_LIST = ['sort', 'ln']
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
    sys.exit(-1)

# Parse and check command line arguments
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

argc = len(sys.argv)
if argc >= 1+1:
    if "--help" == sys.argv[1]:
        PrintHelp()
        sys.exit(0)

modeInspect = False
modeL2M =  False
if argc == 1+2 and "--inspect" == sys.argv[1]:
    modeInspect = True
    if os.path.isdir(sys.argv[2]):
        linkDir = sys.argv[2]
        m3uFile = None
    elif os.path.isfile(sys.argv[2]):
        m3uFile = sys.argv[2]
        linkDir = None
    else:
        print(f"FATAL: given '{sys.argv[2]}' is neither a folder with links nor an M3U playlist")
        PrintHelp()
        sys.exit(0)
elif argc < 1+5 or argc > 1+6:
    PrintHelp()
    sys.exit(-1)
else:
    modeL2M = ('--l2m' == sys.argv[1])
    linkDir = ""
    m3uFile = ""
    baseDir = ""
    extBase = ""
    sortM3U = False
    fullLinks = False
    sepBslash = False   # Whether external path separator is 'backslash' ('\') character, otherwise forward slash

    if modeL2M:
        # links-to-m3u
        linkDir = sys.argv[2]
        m3uFile = sys.argv[3]
        baseDir = sys.argv[4]
        extBase = sys.argv[5]
        sepBslash = ('\\' == extBase[-1])   # Detect backslash-like path formatting from external base directory
        if 1+6 == argc:
            sortM3U = (sys.argv[6] == '--sort-m3u')
            if not sortM3U:
                print("WARNING: invalid argument '"+sys.argv[6]+"'")
    else:
        # m3u-to-links
        m3uFile = sys.argv[2]
        linkDir = sys.argv[3]
        extBase = sys.argv[4]
        baseDir = sys.argv[5]
        if 1+6 == argc:
            fullLinks = (sys.argv[6] == '--full-links')
            if not fullLinks:
                print("WARNING: invalid argument '"+sys.argv[6]+"'")

    if not os.path.isdir(baseDir):
        print(f"FATAL: not a directory '{baseDir}'")
        sys.exit(0)

nOp = 0
# Read the links from folder if it exists
linkEntries = []
if not linkDir is None:
    if os.path.isdir(linkDir):
        contents = os.listdir(linkDir)
        for l in contents:
            lnk = os.path.join(linkDir, l)
            if os.path.islink(lnk):
                linkEntries.append(lnk)
    else:
        os.makedirs(linkDir, exist_ok=True)
    nOp += 1
    print(f"{nOp}. Read {len(linkEntries)} links from folder '{linkDir}'")

# Read the playlist if it exists
playEntries = []
if not m3uFile is None:
    if os.path.isfile(m3uFile):
        with open(m3uFile, 'r') as m3u:
            playEntries = m3u.readlines()
        for i, e in enumerate(playEntries):
            e1 = e
            if e1.endswith('\n'):
                e1 = e1[:-1]
            if e1.endswith('\r'):
                e1 = e1[:-1]
            if e1.endswith('\n'):
                e1 = e1[:-1]
            playEntries[i] = e1
    else:
        os.makedirs(os.path.dirname(m3uFile), exist_ok=True)
    nOp += 1
    print(f"{nOp}. Read {len(playEntries)} entries from playlist '{m3uFile}'")

# Auxiliary functions
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

def CutTrackNo(basename: str) -> str:
    name = basename
    # Cut track number if present
    pos = 0
    for c in name:
        if not c.isdigit():
            break
        pos += 1
    name = name[pos:].lstrip()
    if name[0] in ['.', ',', '-', ':', '|', '∕']:
        name = name[1:].lstrip()
    return name

def AudioName(basename: str) -> str:
    name = CutTrackNo(basename)
    # Cut extension if present
    pos = name.rfind('.')
    if pos > 0:
        name = name[:pos].rstrip()
    return name

def MakeLinkName(audioPath: str) -> str:    # 'audioPath' = real path to real audio file
    # Get parent dir -- album path (incl. year) + track file name
    pathAlbum, fileName = os.path.split(audioPath)
    # Get parent dir -- artist path + album name (incl. year)
    pathArtist, albumName = os.path.split(pathAlbum)
    # Get artist name
    artistName = os.path.basename(pathArtist)

    # Construct link name in form 'Artist - Year - Album - Track'
    return artistName + " ∕ " + albumName + " ∕ " + fileName

def SortTextFile(filePath: str):
    res, err = proc.Popen(["sort", filePath, "-o", filePath], stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
    if len(err) > 0:
        print("WARNING: 'sort' utility returned error message:"+'\n'+err)

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

if modeInspect:
    if not linkDir is None:
        # Convert links into relative ones and rename them as 'Band ∕ Album ∕ ##. Track'
        # --- --- --- --- --- --- --- --- ---
        # Resolve existing links
        nOp += 1
        print(f"{nOp}. Resolving the links from '{linkDir}' ...", end=' ')
        inFiles = []
        nBroken = 0
        for l in linkEntries:
            target = os.path.normpath(os.readlink(l))
            tgt1 = os.path.normpath(os.path.join(linkDir, target))
            if os.path.isfile(target):
                inFiles.append((target, l))
            elif os.path.isfile(tgt1):
                inFiles.append((tgt1, l))
            else:
                nBroken += 1
        print(f"resolved {len(inFiles)} links, ignored {nBroken} broken ones")
        # Convert and rename links
        nOp += 1
        print(f"{nOp}. Inspecting links at '{linkDir}' ...", end=' ')
        nOk = 0
        nErr = 0
        for af, origLink in inFiles:
            lnkPath = os.path.join(linkDir, MakeLinkName(af))   # Design full link path
            res, err = proc.Popen(["ln", "-srf", af, lnkPath], stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
            if len(err) == 0:
                nOk += 1
                if origLink != lnkPath:
                    os.remove(origLink)
            else:
                print("WARNING: 'ln' utility returned error message:"+'\n'+err)
                nErr += 1
        print(f"processed {nOk} links successfully, {nErr} failures occured")

    elif not m3uFile is None:
        # Sort entries in M3U playlist file
        # --- --- --- --- --- --- --- --- ---
        nOp += 1
        print(f"{nOp}. Sorting entries in '{m3uFile}'")
        SortTextFile(m3uFile)
else:
    # Maintain coherence between playlist and a folder with links
    # --- --- --- --- --- --- --- --- ---
    if modeL2M:
        if len(linkEntries) == 0:
            print("Nothing to do, exiting")
            sys.exit(0)
        # Create the list of healthy resolved links from the folder with links
        nOp += 1
        print(f"{nOp}. Resolving the links from '{linkDir}' ...", end=' ')
        inFiles = []
        nBroken = 0
        for l in linkEntries:
            target = os.path.normpath(os.readlink(l))
            tgt1 = os.path.normpath(os.path.join(linkDir, target))
            if os.path.isfile(target):
                inFiles.append(target)
            elif os.path.isfile(tgt1):
                inFiles.append(tgt1)
            else:
                nBroken += 1
        print(f"resolved {len(inFiles)} links, ignored {nBroken} broken ones")

        # Translate links with reference to the local base directory and append them to 'm3u' playlist
        aborted = []
        nOp += 1
        print(f"{nOp}. Appending {len(inFiles)} links into playlist '{m3uFile}' ...")
        with open(m3uFile, 'a') as m3u:
            nApp = 0
            for f in inFiles:
                relPath = os.path.relpath(f, baseDir)       # Relate a file to base dir
                extPath = os.path.join(extBase, relPath)
                if sepBslash:
                    extPath = extPath.replace('/', '\\')    # Convert separators to backslashes if needed
                if not extPath in playEntries:
                    do = input(relPath+" ENTER: ")
                    if len(do) > 0:
                        aborted.append(relPath)
                        continue
                    m3u.write(extPath+'\r\n')
                    nApp += 1
        print(f"   appended {nApp} new entries, avoided {len(inFiles) - nApp} duplicates, aborted {len(aborted)} exiles")
        if len(aborted) > 0:
            print(f"Aborted {len(aborted)} links:")
            for a in aborted:
                print(" "+a)

        # Sort M3U playlist if requested
        if sortM3U:
            SortTextFile(m3uFile)
    
    else:
        if len(playEntries) == 0:
            print("Nothing to do, exiting")
            sys.exit(0)
        # Translate entries from the 'm3u' playlist into the links at link directory
        nOp += 1
        print(f"{nOp}. Converting {len(playEntries)} entries from '{m3uFile}' into local relative links ...")
        nAdd = 0
        nErr = 0
        nDup = 0
        missed = []
        aborted = []
        for e in playEntries:
            extPath = e.replace('\\', '/')  # Convert backslash separators to forward slashes if any
            relPath = os.path.relpath(extPath, extBase)
            locPath = os.path.join(baseDir, relPath)    # Create local path
            if os.path.isfile(locPath):
                fName = os.path.basename(locPath)
                fName = CutTrackNo(fName)
                if fullLinks:
                    lnkPath = os.path.join(linkDir, MakeLinkName(relPath))  # Design full link path
                else:
                    lnkPath = os.path.join(linkDir, fName)  # Design short link path
                doCreate = False
                if not lnkPath in linkEntries:
                    doCreate = True
                else:
                    # Possible duplicate, resolve present link and compare destinations
                    oldDest = os.path.normpath(os.readlink(lnkPath))
                    isHealthy = True
                    if not os.path.isfile(oldDest):
                        oldDest = os.path.normpath(os.path.join(linkDir, oldDest))
                        isHealthy = os.path.isfile(oldDest)
                    # Compare destinations
                    if isHealthy:
                        if os.path.samefile(oldDest, locPath):
                            nDup += 1
                            doCreate = False    # Do not create duplicate links
                        else:
                            # We need to rename the new link to differentiate it from an old one
                            if not fullLinks:
                                # Use Artist and Album names in brakets
                                tgtDir = os.path.dirname(locPath)
                                artPath, albName = os.path.split(tgtDir)
                                artName = os.path.basename(artPath)
                                postfix = ''
                                if len(artName) > 0 and not '/' in artName:
                                    postfix = artName+' ∕ '+albName
                                elif len(albName) > 0 and not '/' in albName:
                                    postfix = albName
                                if len(postfix) == 0:
                                    postfix = str(rnd.randint(1, 99))
                                # Modify local link path
                                postfix = ' ('+postfix+')'
                                pos = lnkPath.rfind('.')
                                if pos > 0:
                                    lnkPath = lnkPath[:pos]+postfix+lnkPath[pos:]
                                else:
                                    lnkPath += postfix
                            # Recheck duplicates again
                            if not lnkPath in linkEntries:
                                # Create the modified link
                                doCreate = True
                            else:
                                # Possible duplicate, resolve present link and compare destinations
                                oldDest = os.path.normpath(os.readlink(lnkPath))
                                isHealthy = True
                                if not os.path.isfile(oldDest):
                                    oldDest = os.path.normpath(os.path.join(linkDir, oldDest))
                                    isHealthy = os.path.isfile(oldDest)
                                # Compare destinations
                                if isHealthy:
                                    if os.path.samefile(oldDest, locPath):
                                        nDup += 1
                                        doCreate = False    # Do not create duplicate links
                                    else:
                                        postfix = ' ('+str(rnd.randint(1, 99))+')'
                                        pos = lnkPath.rfind('.')
                                        if pos > 0:
                                            lnkPath = lnkPath[:pos]+postfix+lnkPath[pos:]
                                        else:
                                            lnkPath += postfix
                # Create the new link if needed
                if doCreate:
                    do = input(lnkPath+"   --->   "+locPath+" ENTER: ")
                    if len(do) > 0:
                        aborted.append(lnkPath)
                        continue
                    # ~ err = ""
                    res, err = proc.Popen(["ln", "-srf", locPath, lnkPath], stdout=proc.PIPE, stderr=proc.PIPE, text=True).communicate()
                    if len(err) == 0:
                        nAdd += 1
                        linkEntries.append(lnkPath)     # Remember the newly added link
                    else:
                        print("WARNING: 'ln' utility returned error message:"+'\n'+err)
                        nErr += 1
            else:
                missed.append(locPath)
        print(f"   added {nAdd} links, skipped {nDup} duplicates, aborted {len(aborted)} exiles, {nErr} failures occured")
        if len(missed) > 0:
            print(f"Missing {len(missed)} local entries (present in playlist, though):")
            for m in missed:
                print(" "+m)
        if len(aborted) > 0:
            print(f"Aborted {len(aborted)} entries in playlist:")
            for a in aborted:
                print(" "+a)

