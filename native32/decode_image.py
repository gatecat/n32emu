from pygame import image
import struct

def decode_image_yuv(data, yuv_dump=None):
    width, height, img_size = struct.unpack("<HHL", data[0:8])
    out = bytearray(width * height * 4)
    y_2_2 = bytearray(width * height)
    u_1_1 = bytearray((width // 2) * (height // 2))
    v_1_1 = bytearray((width // 2) * (height // 2))

    i = 8

    def _putquad(pix, data):
        y = (pix // (width // 2))
        x = (pix % (width // 2))
        # Y
        y_2_2[(2*y)*width + (2*x)] = data[0]
        y_2_2[(2*y+1)*width + (2*x)] = data[1]
        y_2_2[(2*y)*width + (2*x+1)] = data[2]
        y_2_2[(2*y+1)*width + (2*x+1)] = data[3]
        # U
        u_1_1[pix] = data[5]
        v_1_1[pix] = data[4]

    def _clip(v):
        return max(min(v, 255), 0)

        # Interpolation: https://learn.microsoft.com/en-us/windows/win32/medfound/recommended-8-bit-yuv-formats-for-video-rendering#converting-420-yuv-to-422-yuv
    def _interpolate_y(data, w, h):
        h1 = h * 2
        result = bytearray(w * h1)
        for y in range(h):
            for dy in range(2):
                y1 = y * 2 + dy
                for x in range(w):
                    if dy == 0:
                        result[y1 * w + x] = data[y * w + x] if y == 0 or data[y * w + x] != 0 else data[(y - 1) * w + x]
                    else:
                        result[y1 * w + x] = data[y * w + x] if y == (h-1) or data[y * w + x] != 0 else data[(y + 1) * w + x]

        return result


    def _interpolate_x(data, w, h):
        w1 = w * 2
        result = bytearray(w1 * h)
        for y in range(h):
            for x in range(w):
                for dx in range(2):
                    x1 = x * 2 + dx
                    if dx == 0:
                        result[y * w1 + x1] = data[y * w + x] if x == 0 or data[y * w + x] != 0 else data[y * w + (x-1)]
                    else:
                        result[y * w1 + x1] = data[y * w + x] if x == (w - 1) or data[y * w + x] != 0 else data[y * w + (x+1)]

        return result

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




    # yuv = bytearray(width * height * 3)

    u_2_2 = _interpolate_x(_interpolate_y(u_1_1, width // 2, height // 2), width // 2, height)
    v_2_2 = _interpolate_x(_interpolate_y(v_1_1, width // 2, height // 2), width // 2, height)

    if yuv_dump is not None:
        yuv_dump.write(y_2_2)
        yuv_dump.write(u_2_2)
        yuv_dump.write(v_2_2)


    for i in range(width * height):
        if y_2_2[i] == 0: # transparent
            out[i * 4 + 3] = 0
            out[i * 4 + 2] = 0
            out[i * 4 + 1] = 0
            out[i * 4 + 0] = 0
        else:
            # YUV to RGB: https://learn.microsoft.com/en-us/windows/win32/medfound/recommended-8-bit-yuv-formats-for-video-rendering#converting-8-bit-yuv-to-rgb888
            C = y_2_2[i] - 16
            D = u_2_2[i] - 128
            E = v_2_2[i] - 128
            out[i * 4 + 3] = 255
            out[i * 4 + 2] = _clip((298 * C           + 409 * E + 128) >> 8)
            out[i * 4 + 1] = _clip((298 * C - 100 * D - 208 * E + 128) >> 8)
            out[i * 4 + 0] = _clip((298 * C + 516 * D           + 128) >> 8)

    # assert pixel == (width//2) * (height//2)
    return image.frombytes(bytes(out), (width, height), "RGBA")

def decode_image_argb(data):
    width, height, img_size = struct.unpack("<HHL", data[0:8])
    out = bytearray(width * height * 4)

    pixel = 0
    i = 8

    def _putpixel(pix, value):
        y = pix // width
        x = pix % width
        if value & 0x8000 == 0x0:
            out[(y * width + x) * 4 + 3] = 0
            out[(y * width + x) * 4 + 2] = 0
            out[(y * width + x) * 4 + 1] = 0
            out[(y * width + x) * 4 + 0] = 0
        else:
            out[(y * width + x) * 4 + 3] = 255
            out[(y * width + x) * 4 + 2] = ((value >> 0) & 0x1F) << 3 # R
            out[(y * width + x) * 4 + 1] = ((value >> 5) & 0x1F) << 3 # G
            out[(y * width + x) * 4 + 0] = ((value >> 10) & 0x1F) << 3 # B

    while i < img_size+8 and pixel < (width * height):
        op = data[i] | (data[i+1] << 8)
        if op == 0x0:
            # literal 0
            _putpixel(pixel, 0)
            pixel += 1
            i += 2
        elif op & 0xc000 == 0xc000:
            # repeat N times
            value = data[i + 2] | (data[i + 3] << 8)
            for j in range(op & 0x3fff):
                _putpixel(pixel, value)
                pixel += 1
            i += 4
        else:
            assert False, f"0x{op:04x} at 0x{i:06x}"

    return image.frombytes(bytes(out), (width, height), "RGBA")

def main():
    import sys
    with open(sys.argv[1], 'rb') as f:
        header = f.read(0x2000)
        decoded = decode_image_yuv(header[12:])
        image.save(decoded, sys.argv[2])

if __name__ == '__main__':
    main()
