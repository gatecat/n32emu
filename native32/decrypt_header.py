import struct
import sys
from des_constants import *


def _expand_bits(data, count):
    result = bytearray(count)
    for i in range(count):
        result[i] = (data[i >> 3] >> (i & 7)) & 1
    return result

def _compress_bits(data, count):
    result = bytearray(count // 8)
    for i in range(count):
        result[i >> 3] |= data[i] << (i & 7)
    return result

def _do_shuffle(dst, src, table, count, offset = 0):
    temp = bytearray(count)
    for i in range(count):
        temp[i] = src[table[i] - 1]
    for i in range(count):
        dst[i + offset] = temp[i]

def _slice_and_dice(src, count, splitpoint, offset = 0):
    shuffle_temp = bytearray(src[offset:offset+splitpoint])
    for i in range(count - splitpoint):
        src[offset + i] = src[offset + i + splitpoint]
    for i in range(splitpoint):
        src[offset + i + (count - splitpoint)] = shuffle_temp[i]

def _expand_key(src):
    key_bits = _expand_bits(src, 0x40)
    _do_shuffle(key_bits, key_bits, INITIAL_KEY_PERMUTATION, 0x38)
    result = bytearray(0x30*0x10)
    for i in range(0x10):
        splitpoint = KEY_SHIFT_SIZES[i]
        _slice_and_dice(key_bits, 0x1c, splitpoint)
        _slice_and_dice(key_bits, 0x1c, splitpoint, 0x1c)
        _do_shuffle(result, key_bits, SUB_KEY_PERMUTATION, 0x30, i * 0x30)
    return result

def _do_xor(data, key, count):
    for i in range(count):
        data[i] = data[i] ^ key[i]

def _do_sbox(data, key):
    for i in range(8):
        k = key[i*6:(i+1)*6]
        idx = (i * 4 + k[5] + k[0] * 2) * 0x10 + (k[4] + k[1] * 8 + k[2] * 4 + k[3] * 2)
        bits = _expand_bits(DES_SBOXES[idx:idx+1], 4)
        for j in range(4):
            data[i*4+j] = bits[j]

def _process_iteration(data, key):
    iter_temp = bytearray(0x30)
    _do_shuffle(iter_temp, data, MESSAGE_SHUFFLE, 0x30)
    _do_xor(iter_temp, key, 0x30)
    _do_sbox(data, iter_temp)
    _do_shuffle(data, data, RIGHT_SUB_MESSAGE_PERMUTATION, 0x20)

def _decrypt_chunk(src, expanded_key):
    expanded_data = _expand_bits(src, 0x40)
    _do_shuffle(expanded_data, expanded_data, INITIAL_MESSAGE_PERMUTATION, 0x40)
    for i in range(0x2d0, -1, -0x30):
        temp_data = bytearray(expanded_data[:0x20])
        _process_iteration(expanded_data, expanded_key[i:i+0x30])
        _do_xor(expanded_data, expanded_data[0x20:0x40], 0x20)
        for j in range(0x20):
            expanded_data[0x20+j] = temp_data[j]
    _do_shuffle(expanded_data, expanded_data, FINAL_MESSAGE_PERMUTATION, 0x40)
    return _compress_bits(expanded_data, 0x40)

def do_decrypt(data, key):
    expanded_key = _expand_key(key)
    result = bytearray()
    for i in range(len(data) // 8):
        result.extend(_decrypt_chunk(data[i*8:(i+1)*8], expanded_key))
    return result

def decrypt_header(data):
    keys = b'1111111122222222aaaaaaaabbbbbbbbaber3801'
    for i in range(5):
        key = keys[i*8:(i+1)*8]
        decrypted = do_decrypt(data, key)
        if decrypted[4:8] == b'8202':
            print(f"using key {key}")
            return decrypted
    assert False, "key not found"


if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        data = f.read()
        data = bytearray(data)
        idx = 0
        idx += 0x1800 # thumb
        prefix = data[idx:idx+0x60]
        idx += 0x60
        assert prefix[0:4] == b'_YUV', prefix
        header = data[idx:idx+0x40]

        decrypted = decrypt_header(header[0x18:])
        data[idx+0x18:idx+0x40] = decrypted

    with open(sys.argv[2], 'wb') as f:
        f.write(data)
