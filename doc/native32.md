# The Native32 Game Format

Native32 is a game format developed by Sunplus for its DVD player and TV chipsets. Around 2008-10 it saw the most use in
adding game functionality to portable DVD players, car headrest display, etc.

There are some loose similarities to Flash in the data model and its use of an ActionScript-like virtual machine (using the same
opcodes but a different, simplified bytecode encoding). Unlike Flash, however, Native32 is entirely a raster format and all 
animations and transitions are done using a series of raster frames.

Native32 files generally have a `.smf`, `.sgm` or `.ssl` extension. `SSL` seems to relate to the games split across multiple files.

The format is generally little endian. This document isn't intended to be a complete or rigorous reference to the format - it's not even understood to that extent - but to cover the trickier and more interesting parts.

## Thumbnail

The first thing in the file is usually a thumbnail, although this is optional. The 4 bytes `SWFT` tag the presence of a thumbnail,
followed by a colourspace indicator (`_YUV` or `ARGB`). There are then 4 bytes of flags, followed by a Native32 image (details on the format follow).
Important here is that after 2 bytes of width and height, there's 4 bytes for image size so it can be skipped over.

## Header

After the thumbnails and zero-padding to align to a 0x200 boundary, the Native32 file itself starts. This is once again a colourspace flag (e.g. `_YUV`), followed by 0x60 bytes containing the name of the program that generated it (`Gamemaker 1.3.12`).

0x60 bytes after the start of the colourspace flag is the base offset added to all other offsets in the file.

Here also begins the header. The first 8 bytes contains 2 bytes each for some flags, and three other values that don't seem to be used.

After this is 4 bytes each for load address (seemingly zero), binary size, MP3 offset and a value that should be the size of the MP3 data but is always zero.

The subsequent 32 bytes of header are encrypted. Once decrypted, the first 4 bytes serve a purpose unknown, followed by the fixed string `8202` (SPHE8202 was presumably the first chipset to ship with Native32) which is used to make sure the decryption worked.

The remaining 24 bytes after decryption contain the offsets (4 bytes each) to
 - the list of frames
 - list of images
 - "Action" bytecode
 - list of movies
 - list of "buttons"
 - list of button events.

Next is apparently a mouse cursor (unused), 2 bytes each for width and height followed by 16bpp image data.

The final part of the header is a list of offsets to sounds (4 bytes per sound item).

### Header Encryption

The header encryption is supposed to be DES in ECB mode, with the following 5 keys tried in sequence until the `8202` string in positions 4-8 of the decrypted output is identified: `11111111`, `22222222`, `aaaaaaaa`, `bbbbbbbb` and `aber3801`.
The final key must be the production one, as it is always the one used. The DES implementation does not seem to match the standard one, however, hence the custom implementation used in the emulator.

## Frames

The frame table pointed to in the header contains a list of offsets (4 bytes each) to the contents of each frame (important - all offsets from hereon in are relative to the base mentioned above, usually 0x1860 into the file).

The first frame is frame 1, not 0. This applies to all the other tables; including images, movies, sounds and Action bytecode.

Frames themselves are a list of entries, 16 bytes each, split up as follows:

 - 2 bytes: type of object (0=end of list, 1=image, 2=movie, 3=button, 4=action, 5=sound)
 - 2 bytes: index of the object (e.g. into the image table or Action bytecode)
 - 2 bytes: X
 - 2 bytes: Y
 - 2 bytes: depth
 - 2 bytes: unused
 - 4 bytes: pointer to a string for the object name (optional, generally only used for movies)

## Images

The image table contains a list of 4-byte offsets to images.

Images themselves each start with an 8-byte header: 2 bytes each for width and height and 4 bytes for image size in bytes (excluding header.

For YUV images, image data itself is then encoded as YUV 4:2:0 with a "packbits"-like compression algorithm.

A 2-byte value specifies how to interpret the following data. If the MSB is set, it means, read N x 6-byte chunks of pixel data; if it is cleared, read a 6-byte chunk of pixel data and repeat it N times.

Each 6-byte chunk represents 4 pixels; with 4 Y values (ordered x0y0, x0y1, x1y0, x1y1); U and V.

The case of Y=0 is transparent. Interpolation of YUV 4:2:0 isn't fully understood but seems to require taking non-zero U/V values from adjacent pixels for cases where U=0 and V=0.

For ARGB images, image data uses a ARGB1555 pixel format. The compression also works a bit different - the only two possibilities I've seen for the two-byte "command are" 0x0000 for a literal single transparent, otherwise the top two MSBs are set which means repeat the following pixel N times.

## Movies

Movies are not just used for animation but as sprites in general.

They can be given names inside a frame; and programmatically have their position, visibility or frame number modified, as well as execute events when they reach a frame.

They can also be programmatically created using the `CloneSprite` operation.

Movies, as pointed to by their entry in the movie table, are stored in the file as a list of movie frames. Each frame is 12 bytes:

 - 2 bytes: image index (0xFFFF ends the movie)
 - 2 bytes: X offset
 - 2 bytes: Y offset
 - 2 bytes: if non-zero, index of Action code to execute
 - 2 bytes: if non-zero, sound to play. The first byte is the sound index and the next the number of times to loop (0xFF=indefinite)
 - 2 bytes: seemingly unused

## Buttons

Buttons as rendering objects seem to be safely ignored (they always point to off-screen images); as there is no mouse input support.

However, off-screen buttons are used to receive keyboard events, so button events are still important. For each button, the button event table contains a 4-byte pointer to the list of button events.

The list of button events starts with a 2-byte value that is the total number of action operations associated with the button. Then, for each event, there are 6 bytes:

 - 2 bytes: keycode
 - 2 bytes: number of action operations for this event
 - 2 bytes: index into action table when event triggered

The table ends when the total number of action operations is reached. The following keycodes have been observed:

keycode | button
--------|-------------
0x0200  | left
0x0400  | right
0x1c00  | up
0x1e00  | down
0x4000  | A
0x8800  | B/menu

## Action bytecode

Native32 uses a stack-based, stringly-typed virtual machine based on the ActionScript Virtual Machine.
The opcodes it uses are the same (see [actions.py](../native32/actions.py) for a list) but the bytecode encoding is different.
All instructions are encoded as 4-bytes for the opcode (even though it only ever uses 1 byte) and 4-bytes for the payload.

For most opcodes that take a payload, the payload value is a pointer to a null-terminated string.
However, for those that always take a numeric argument (`Action.If`, `Action.GotoFrame`, `Action.GotoFrame2`, and `Action.Jump`) the payload is a pointer to a 2-byte integer.

Indexes into the bytecode (e.g. for frame, movie and button events) are always in terms of instructions, rather than bytes, and are one-based. Jumps are relative in terms of instructions, with one added if the jump value is positive.

There are cases where Native32 games attempt to access variables in with the name in a different case to when they were set. It is unclear if the VM is actually intended to be case-insensitive, or if this is a bug in these games that was not caught because undefined variables defaulting to empty.

The `GetUrl2` instruction is special, behaving differently to in ActionScript, and used to execute functions outside of defined actions. The `target` parameter (second argument) determines what to do. The following have been seen (`<var>` means the name of a variable to be set). `<success>` is the name of a variable that is set to `S` in the case of success (failure value is not known).

Target                            | Value     | Meaning
----------------------------------|-----------|---------
`SSL+SSL_PlayNext+<success>`      | `file`    | Load the content from `file` and play it. Multiple files can be specified, separated by `+`, this is used to play an intro cutscene in MPEG format before loading the game content.
`SSL+SSL_PlayPlan+<success>`      | unknown   | Used in some way to generate loading bar after `SSL_PlayNext`
`SSL+SSL_PlayProg+<success>`      | unknown   | Seems similar to `SSL_PlayProg`
`SSL+SSL_GetSSLData+<success>`    | `<data>`  | Load save data into `<data>`
`SSL+SSL_SaveSSLData+<success>`   | `data`    | Save the data `data`
`NAV+NAV_ScreenMove+<success>`    | `x+y`     | Shift the entire screen by `x` and `y` pixels (used for a screen shake effect in Rune Word)

## Execution model

The execution model is still not fully accurately understood, leading to issues in some games, but this model is what is currently emulated and seems to cause reasonable behaviour in most cases:

 - Frames run at 30fps
 - Movies run at half the framerate of frames, and loop automatically. Movies wait for sounds to finish before continuing.
 - Frame actions run before movie actions
 - The `GotoFrame` instruction actually moves to one frame more than the payload. This does not apply to `GotoFrame2`

## Sounds

The sound table contains a list of pointers to sound data, 4-bytes each. The first 4 bits of the pointer are masked off and determine the type of the sound data.

If the type is 0xF, then the sound data is in MP3 format. The sound data is prefixed by a 6-byte header, the first 4 bytes containing the length of  the data.

If the type is 0x0, then the sound data is raw 16-bit mono samples, prefixed by a 4-byte length value.
In YUV mode, these are big-endian and played at 11025Hz, in ARGB mode, they are little-endian and played at 22050Hz.


