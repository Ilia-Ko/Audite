#!/bin/bash

# This script takes a directory and loops through the subdirectories
# trying to use CUE files to split corresponding FLAC/APE/M4A/WV/MP3
# files. 'Corresponding' means that cuesheet and audio file are
# named identically, apart from extension:
#       'album.cue' corresponds to 'album.flac'
#
# ARG1: path to album collection (e.g. artist/band folder)

# Alternative splitters (see 'SplitByCUE' function below):
# > cue2tracks -R -C -c flac -p path/to/picture.jpg -o "%N. %t" path/to/CueFile.cue
# > split2flac -of "@track. @title.@ext" -f flac -c path/to/picture.jpg -cs 1000x1000 -nd -cue path/to/CueFile.cue path/to/Source.flac

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

# Find an appropriate image in current working directory such as 'cover.jpg', 'folder.jpg', 'front.jpg' or any 'jp(e)g'
function FindImage {
    des="cover.jpg"
    if [ -f "$des" ]; then
        echo "$des"
    else
        find . -type f -iname '*cover*.jp*g' -exec mv -n {} "$des" \;
        if [ -f "$des" ]; then
            echo "$des"
        else
            find . -type f -iname '*folder*.jp*g' -exec mv -n {} "$des" \;
            if [ -f "$des" ]; then
                echo "$des"
            else
                find . -type f -iname 'front.jp*g' -exec mv -n {} "$des" \;
                if [ -f "$des" ]; then
                    echo "$des"
                else
                    find . -type f -iname '*.jp*g' -exec mv -n {} "$des" \;
                    if [ -f "$des" ]; then
                        echo "$des"
                    else
                        echo ""
                    fi
                fi
            fi
        fi
    fi
}

# Embed metadata into FLAC file:
# $1 = path to FLAC file
# $2 = track title
# $3 = track number
# $numTracks, $albumPerf, $albumDate, $albumName and $albumGenre
# $imgCover (optional) = path to cover image to be embedded into FLAC
function ForceTagsFLAC {
    metaflac --remove-tag=TITLE "$1"
    metaflac --remove-tag=TRACKNUMBER "$1"
    metaflac --remove-tag=TRACKTOTAL "$1"
    metaflac --remove-tag=ARTIST "$1"
    metaflac --remove-tag=DATE "$1"
    metaflac --remove-tag=ALBUM "$1"
    metaflac --remove-tag=GENRE "$1"
    metaflac --remove-tag=DESCRIPTION "$1"
    metaflac --remove-tag=encoder "$1"
    metaflac --remove-tag=LOG --remove-tag=log "$1"
    metaflac --set-tag=TITLE="$2" "$1"
    metaflac --set-tag=TRACKNUMBER="$3" "$1"
    metaflac --set-tag=TRACKTOTAL="$numTracks" "$1"
    metaflac --set-tag=ARTIST="$albumPerf" "$1"
    metaflac --set-tag=DATE="$albumDate" "$1"
    metaflac --set-tag=ALBUM="$albumName" "$1"
    metaflac --set-tag=GENRE="$albumGenre" "$1"
    metaflac --remove --block-type=SEEKTABLE "$1"
    metaflac --remove --block-type=APPLICATION "$1"
    if ! [ -z "$imgCover" ]; then
        metaflac --remove --block-type=PICTURE "$1"
        metaflac --import-picture-from="$imgCover" "$1"
    fi
}

# Embed metadata into MP3 file:
# $1 = path to MP3 file
# $2 = track title
# $3 = track number
# $numTracks, $albumPerf, $albumDate, $albumName and $albumGenre
# $imgCover (optional) = path to cover image to be embedded into MP3
function ForceTagsMP3 {
    mid3v2 -t "$2" -T "$3/$numTracks" -a "$albumPerf" -A "$albumName" -y "$albumDate" -g "$albumGenre" -p "$imgCover" "$1"
    if ! [ -z "$imgCover" ]; then
        mid3v2 --delete-frames=APIC "$1"
        mid3v2 -p "$imgCover" "$1"
    fi
}

# Split long audio file into multiple tracks and annotate them:
# $1 = input audio file to be splitted
# $2 = cuesheet defining splitpoints (timecodes) and track metadata
# Cover image is also embedded if present in the album directory.
function SplitByCUE {
    if ! [ -f "$1" ] || ! [ -f "$2" ]; then
        echo "Please, specify existing 'source.flac' and 'cuesheet.cue' as arguments"
        exit
    fi
    echo "=== === === === === ==="
    pwd
    echo "Split audio: '$1'"
    echo "Splitpoints: '$2'"
    splitDir="."
    # Keep complex album structure now, can be flattened later by Audite.py
    if [[ "$2" =~ "CD1" ]]; then
        mkdir -p "CD1"
        splitDir="CD1"
    elif [[ "$2" =~ "CD2" ]]; then
        mkdir -p "CD2"
        splitDir="CD2"
    elif [[ "$2" =~ "CD3" ]]; then
        mkdir -p "CD3"
        splitDir="CD3"
    elif [[ "$2" =~ "Bonus" ]]; then
        mkdir -p "Bonus CD"
        splitDir="Bonus CD"
    fi
    echo "Dest.folder: '$splitDir'"
    if [[ "$splitDir" != "." ]]; then
        mv "$1" "$splitDir/$1"
        mv "$2" "$splitDir/$2"
    fi

    # Find a cover image
    image="$(FindImage)"

    # Obsolete splitters
    #~ if [[ "$1" =~ ".flac" ]]; then
        #~ shnsplit -f "$2" -o flac -d "$splitDir" -t "%n. %t" "$1"
        #~ mv "$1" "$1"0   # Move input FLAC to FLAC0 (delete later all *.flac0 files)
        #~ find . -type f -iname '*.flac' -print0 | sort -z | xargs -r0 cuetag.sh "$2"
    #~ else
        #~ mp3splt -c "$2" -d "$splitDir" -o "@n2. @t" "$1"
        #~ mv "$1" "$1"0   # Move input MP3 to MP30 (delete later all *.mp30 files)
        #~ find . -type f -iname '*.mp3' -print0 | sort -z | xargs -r0 cuetag.sh "$2"
    #~ fi

    initWD=$(pwd)
    srcAudio=$(basename "$1")
    cueSheet=$(basename "$2")
    if [[ -f "$image" ]]; then
        imgCover=$(realpath "$image")
        echo "Using cover image '$imgCover'"
    else
        echo "Cover image not found"
        imgCover=""
    fi
    cd "$splitDir"

    # Identify source file type: FLAC or MP3
    ext=${srcAudio##*.}
    ext=${ext,,}
    if [ "$ext" != "flac" ] && [ "$ext" != "mp3" ]; then
        echo "Unsupported file type, we only accept FLAC or MP3 on this stage"
        exit
    fi

    # Ensure UTF-8 encoding of cuesheet file
    encoding="$(file -bi "$cueSheet")"
    encoding=${encoding#*charset=}
    if [ "$encoding" != "utf-8" ] && [ "$encoding" != "us-ascii" ]; then
        echo "WARNING: Suspicious encoding '$encoding' of cueSheet"
        mv "$cueSheet" "$cueSheet.orig"
        iconv -f "windows-1251" -t "utf-8" "$cueSheet.orig" > "$cueSheet"
    fi

    # Retrieve some metadata from cuesheet file
    albumName=$(grep -m1 -w "TITLE" "$cueSheet")
    albumName=${albumName#*\"}
    albumName=${albumName%\"*}
    albumGenre=$(grep -m1 -w "REM GENRE" "$cueSheet")
    albumGenre=${albumGenre#REM GENRE }
    albumGenre=${albumGenre#*\"}
    albumGenre=${albumGenre%\"*}
    albumDate=$(grep -m1 -w "REM DATE" "$cueSheet" | tr -d '\r' | awk '{ print $3 }')
    albumPerf=$(grep -m1 -w "PERFORMER" "$cueSheet")
    albumPerf=${albumPerf#*\"}
    albumPerf=${albumPerf%\"*}
    if [ -z "$albumPerf" ] || [ -z "$albumDate" ] || [ -z "$albumName" ] || [ -z "$albumGenre" ]; then
        echo "Please, add 'TITLE', 'REM DATE', 'PERFORMER' and 'REM GENRE' into cuesheet header"
        exit
    fi

    # Create intermediate file with track titles and count the total number of tracks
    titleFile="$cueSheet-titles.txt"
    grep -w TITLE "$cueSheet" | tail +2 > "$titleFile"
    cntTracks=$(wc -l "$titleFile")
    cntTracks=${cntTracks%%\ *}
    printf -v numTracks "%02d" $cntTracks

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

    ts0="0.00"
    trackNo=1
    for ts in $(cuebreakpoints "$cueSheet")
    do
        # Convert cuesheet timestamp 'ts' from 'min:sec.ms' into 'sec.ms' format
        ts1Sec=${ts#*:}
        ts1Min=${ts%:*}
        ts1=$(python -c "print(round("$ts1Min"*60+"$ts1Sec",2))")
        # Format track number like '01'
        printf -v strNo "%02d" $trackNo
        # Obtain track title
        strTitle=$(head -n $trackNo "$titleFile" | tail -n 1 | tr '/' '|')
        strTitle=${strTitle#*\"}
        strTitle=${strTitle%\"*}
        # Show output file name
        outFile="$strNo. $strTitle.$ext"
        echo "$strNo. From '$ts0' to '$ts1' track '$strTitle'"
        # Process audio depending on file type
        if [ "$ext" = "flac" ]; then
            # Cut source FLAC between defined timestampes
            ffmpeg -hide_banner -y -v error -i "$srcAudio" -ss $ts0 -to $ts1 -c:a flac -map_metadata 0 "$outFile"
            # Ensure valid and comprehensive metadata in FLAC file
            ForceTagsFLAC "$outFile" "$strTitle" "$strNo"
        elif [ "$ext" = "mp3" ]; then
            # Cut source MP3 between defined timestampes
            ffmpeg -hide_banner -y -v error -i "$srcAudio" -ss $ts0 -to $ts1 -c:a libmp3lame -map_metadata 0 "$outFile"
            # Ensure valid and comprehensive metadata in MP3 file
            ForceTagsMP3 "$outFile" "$strTitle" "$strNo"
        fi
        # Move on to the next track
        ts0=$ts1
        trackNo=$(($trackNo+1))
    done

    # Process the last last track, format its number like '09'
    printf -v strNo "%02d" $trackNo
    # Obtain the last track title
    strTitle=$(head -n $trackNo "$titleFile" | tail -n 1 | tr '/' '|')
    strTitle=${strTitle#*\"}
    strTitle=${strTitle%\"*}
    # Show the last output file name
    outFile="$strNo. $strTitle.$ext"
    echo "$strNo. From '$ts0' to 'the end' track '$strTitle'"
    # Process the last audio depending on file type
    if [ "$ext" = "flac" ]; then
        # Cut source FLAC after the last timestamp
        ffmpeg -hide_banner -y -v error -i "$srcAudio" -ss $ts0 -c:a flac -map_metadata 0 "$outFile"
        # Ensure valid and comprehensive metadata in FLAC file
        ForceTagsFLAC "$outFile" "$strTitle" "$strNo"
    elif [ "$ext" = "mp3" ]; then
        # Cut source MP3 after the last timestamp
        ffmpeg -hide_banner -y -v error -i "$srcAudio" -ss $ts0 -c:a libmp3lame -map_metadata 0 "$outFile"
        # Ensure valid and comprehensive metadata in MP3 file
        ForceTagsMP3 "$outFile" "$strTitle" "$strNo"
    fi

    # --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

    # Clean up
    rm "$titleFile"             # Delete auxiliary file
    mv "$srcAudio" "$srcAudio"0 # Mark source file as processed, but do not delete it
    cd "$initWD"                # Return back to caller directory
}

# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---
# ENTRY POINT - Execution starts here
# --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---

# Check the only argument: base directory to scan for albums recursively
base="$1"
if [ -z "$base" ]; then
    echo "Please, specify input base directory as the only argument"
    exit
elif [ ! -d "$base" ]; then
    echo "Cannot access '$base', please, check it"
    exit
fi
echo "Got base directory: $1"

returnWD=$(pwd)

# Obtain complete list of cuesheets down the base directory
readarray -d '' cueSources < <(find "$base" -type f -iname "*.cue" -print0)

# Loop through the list of cuesheets
for cueSrc in "${cueSources[@]}"; do
    cueDir=$(dirname "$cueSrc")
    cueFile=$(basename "$cueSrc")
    cd "$cueDir"
    flacFile="${cueFile%.*}.flac"
    mp3File="${cueFile%.*}.mp3"
    apeFile="${cueFile%.*}.ape"
    m4aFile="${cueFile%.*}.m4a"
    wvFile="${cueFile%.*}.wv"
    # Look for an audio file to split
    if [ -f "$apeFile" ]; then
        # Convert APE file to FLAC
        ffmpeg -hide_banner -y -v error -i "$apeFile" -acodec flac -map_metadata 0 "$flacFile"
    elif [ -f "$m4aFile" ]; then
        # Convert M4A file to FLAC
        ffmpeg -hide_banner -y -v error -i "$m4aFile" -acodec flac -map_metadata 0 "$flacFile"
    elif [ -f "$wvFile" ]; then
        # Convert WV file to FLAC
        ffmpeg -hide_banner -y -v error -i "$wvFile" -acodec flac -map_metadata 0 "$flacFile"
    fi
    # Do actual splitting
    if [ -f "$flacFile" ]; then
        SplitByCUE "$flacFile" "$cueFile"
    elif [ -f "$mp3File" ]; then
        SplitByCUE "$mp3File" "$cueFile"
    fi
    cd "$returnWD"
done
