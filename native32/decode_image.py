from PIL import Image
import struct

def decode_image(data):
    width, height, img_size = struct.unpack("<HHL", data[0:8])
    out = bytearray(width * height * 3)
    i = 8
    def _putxy(x, y, l, cr, cb):
        cr -= 128
        cb -= 128
        out[(y * width + x) * 3 + 2] = min(max(l + (45 * cr) // 32, 0), 255)
        out[(y * width + x) * 3 + 1] = min(max(l - (11 * cb + 23 * cr) // 32, 0), 255)
        out[(y * width + x) * 3 + 0] = min(max(l + (113 * cb) // 64, 0), 255)
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
        assert op != 0x0
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
    assert pixel == (width//2) * (height//2)
    return Image.frombytes("RGB", (width, height), out)

