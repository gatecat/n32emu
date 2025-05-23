# The Native32 Game Format

Native32 is a game format developed by Sunplus for its DVD player and TV chipsets. Around 2008-10 it saw the most use in
adding game functionality to portable DVD players, car headrest display, etc.

There are some loose similarities to Flash in the data model and its use of an ActionScript-like virtual machine (using the same
opcodes but a different, simplified bytecode encoding). Unlike Flash, however, Native32 is entirely a raster format and all 
animations and transitions are done using a series of raster frames.

Native32 files generally have a `.smf` or `.ssl` extension. `SSL` (nothing to do with secure sockets!) seems to relate to the games split across multiple files.

The format is generally little endian. This document isn't intended to be a complete or rigorous reference to the format - it's not even understood to that extent - but to cover the trickier and more interesting parts.

## Thumbnail

The first thing in the file is usually a thumbnail, although this is optional. The 4 bytes `SWFT` tag the presence of a thumbnail,
followed by a colourspace indicator (`_YUV` or `ARGB`). Only the YUV variant is supported and discussed here, I haven't seen the
`ARGB` one in the wild. There are then 4 bytes of flags, followed by a Native32 image (details on the format follow).
Important here is that after 2 bytes of width and height, there's 4 bytes for image size so it can be skipped over.

## Header

After the thumbnails and zero-padding to align to a 0x200 boundary, the Native32 file itself starts. This is once again a colourspace flag (`_YUV`), followed by 0x60 bytes containing the name of the program that generated it (`Gamemaker 1.3.12`).

0x60 bytes after the start of the colourspace flag is the base offset added to all other offsets in the file.

Here also begins the header. The first 8 bytes contains 2 bytes each for some flags, and three other values that don't seem to be used.

After this is 4 bytes each for load address (seemingly zero), binary size, MP3 offset and a value that should be the size of the MP3 data but is always zero.

The subsequent 32 bytes of header are encrypted. Once decrypted, the first 4 bytes serve a purpose unknown, followed by the fixed string `8202` (SPHE8202 was presumably the first chipset to ship with Native32) which is used to make sure the decryption worked.

The remaining 24 bytes after decryption contain the offsets to the list of frames; list of images; "Action" bytecode; list of movies; list of "buttons" and list of button events.

Next is apparently a mouse cursor (unused), 2 bytes each for width and height followed by 16bpp image data.

The final part of the header is a list of offsets to sounds.

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

The image data itself is then encoded as YUV 4:2:0 with a "packbits"-like compression algorithm.

A 2-byte value specifies how to interpret the following data. If the MSB is set, it means, read N x 6-byte chunks of pixel data; if it is cleared, read a 6-byte chunk of pixel data and repeat it N times.

Each 6-byte chunk represents 4 pixels; with 4 Y values (ordered x0y0, x0y1, x1y0, x1y1); U and V.

The case of U=0 and V=0 is transparent.

## Movies

Movies are not just used for animation but as sprites in general.

They can be given names inside a frame; and programmatically have their position, visibility or frame number modified, as well as execute events when they reach a frame.

They can also be programmatically created using the `CloneSprite` operation.

Movies, as pointed to by their entry in the movie table, are stored in the file as a list of movie frames. Each frame is 12 bytes:

 - 2 bytes: image index (0xFFFF ends the movie)
 - 2 bytes: X offset
 - 2 bytes: Y offset
 - 2 bytes: if non-zero, index of Action code to execute
 - 2 bytes: if non-zero, sound to play
 - 2 bytes: seemingly unused

## Buttons

Buttons as rendering objects seem to be safely ignored; as there is no mouse input support.

However, off-screen buttons are used to receive keyboard events, so button events are still important.

