import sys
import struct

with open(sys.argv[1], "rb") as mmp:
    mmpi_hdr = mmp.read(0x10)
    assert mmpi_hdr[0:4] == b'MMPi'
    mmpd_hdr = mmp.read(0x24)
    assert mmpd_hdr[0:4] == b'MMPd'
    len_segments, = struct.unpack('<I', mmpd_hdr[0x14:0x18])
    entry_point, = struct.unpack('<I', mmpd_hdr[0x18:0x1C])

    print(f"{len_segments} segments")
    print(f"Entry point: 0x{entry_point:08x}")
    for i in range(len_segments):
        mmps_hdr = mmp.read(0x18)
        assert mmps_hdr[0:4] == b'MMPs', (mmps_hdr, )
        seg_size, = struct.unpack('<I', mmps_hdr[0x04:0x08])
        paddr, = struct.unpack('<I', mmps_hdr[0x08:0x0C])
        vaddr, = struct.unpack('<I', mmps_hdr[0x0C:0x10])
        seg_data = mmp.read(seg_size - 0x18)
        print(f"Segment {i}:")
        print(f"    Phys 0x{paddr:08x} Virt 0x{vaddr:08x} Len {seg_size-0x18}")

        if len(seg_data) > 0:
            with open(f"seg_0x{paddr:08x}.bin", "wb") as b:
                b.write(seg_data)
