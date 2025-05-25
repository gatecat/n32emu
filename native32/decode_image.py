from pygame import image
import struct

def decode_image(data, yuv_dump=None):
    width, height, img_size = struct.unpack("<HHL", data[0:8])
    out = bytearray(width * height * 4)
    if yuv_dump is not None:
        yuv = bytearray(width * height * 3)
    i = 8
    def _putxy(x, y, l, cr, cb):
        if yuv_dump is not None:
            yuv[(y * width + x) * 3 + 0] = l
            yuv[(y * width + x) * 3 + 1] = cr
            yuv[(y * width + x) * 3 + 2] = cb

        if cr == 0 and cb == 0:
            out[(y * width + x) * 4 + 3] = 0
            out[(y * width + x) * 4 + 2] = 0
            out[(y * width + x) * 4 + 1] = 0
            out[(y * width + x) * 4 + 0] = 0
        else:
            cr -= 128
            cb -= 128
            out[(y * width + x) * 4 + 2] = min(max(l + (45 * cr) // 32, 0), 255)
            out[(y * width + x) * 4 + 1] = min(max(l - (11 * cb + 23 * cr) // 32, 0), 255)
            out[(y * width + x) * 4 + 0] = min(max(l + (113 * cb) // 64, 0), 255)
            out[(y * width + x) * 4 + 3] = 255

    def _putquad(pix, data):
        y = (pix // (width // 2))
        x = (pix % (width // 2))
        _putxy(2*x, 2*y, data[0], data[4], data[5])
        _putxy(2*x+1, 2*y, data[2], data[4], data[5])
        _putxy(2*x, 2*y+1, data[1], data[4], data[5])
        _putxy(2*x+1, 2*y+1, data[3], data[4], data[5])

    pixel = 0
    while i < img_size+8 and pixel < ((width//2) * (height//2)):
        op = data[i] + (data[i+1] << 8)
        assert op != 0x0, f"0x{i:08x}"
        i += 2
        if op & 0x8000 != 0:
            # N quads of data
            op &= ~0x8000
            for j in range(op):
                _putquad(pixel, data[i:i+6])
                pixel += 1
                i += 6
        else:
            # repeat N times
            for j in range(op):
                _putquad(pixel, data[i:i+6])
                pixel += 1
            i += 6
    if yuv_dump is not None:
        yuv_dump.write(yuv)
    # assert pixel == (width//2) * (height//2)
    return image.frombytes(bytes(out), (width, height), "RGBA")

def main():
    import sys
    with open(sys.argv[1], 'rb') as f:
        header = f.read(0x2000)
        decoded = decode_image(header[12:])
        image.save(decoded, sys.argv[2])

if __name__ == '__main__':
    main()
