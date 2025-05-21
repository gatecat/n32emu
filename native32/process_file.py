import sys, struct
from pathlib import Path

from decrypt_header import decrypt_header
from decode_image import decode_image
from actions import Action
from decompile import decompile

from enum import IntEnum

class ObjectType(IntEnum):
    Image = 1
    Movie = 2
    Button = 3
    Action = 4
    Sound = 5

class Native32Reader:
    def __init__(self, f):
        self.data = f.read()
        self.idx = 0
    def skip_thumbnail(self):
        if self.data[self.idx:self.idx+4] == b'SWFT':
            # thumbnail
            self.idx += 4
            thumb_header = self.data[self.idx:self.idx+0x10]
            colorspace, flags, width, height, size = struct.unpack("<4slhhl", thumb_header)
            print(f"Thumbnail: {colorspace.decode('utf-8')} {width}x{height}")
            self.thumbnail = bytes(self.data[self.idx:self.idx+0x10+size])
            self.idx += 0x10
            self.idx += size

    def find_header(self):
        while self.idx < len(self.data) - 4:
            magic = self.data[self.idx:self.idx+4]
            if magic in (b'_YUV', b'ARGB'):
                self.colorspace = magic.decode('utf-8')
                print(f"Found {self.colorspace} Native32 header at 0x{self.idx:x}")
                return
            self.idx += 1
        assert False, "Native32 header not found"

    def process_header(self):
        self.generator = struct.unpack("<32s", self.data[self.idx+0x4:self.idx+0x24])[0].decode('utf-8')
        print()
        print(f"   Generator:        {self.generator}")
        self.idx += 0x60
        self.base = self.idx
        self.fps_color_size, self.action_stack_var, self.button_movieclip, self.buffer_sound = struct.unpack('<HHHH', self.data[self.idx:self.idx+0x08])
        self.idx += 0x08
        self.load_addr, self.binary_size, self.mp3_offset, self.mp3_length = struct.unpack("<LLLL", self.data[self.idx:self.idx+0x10])
        self.idx += 0x10
        print(f"   FPS/color/size:   0x{self.fps_color_size:04x}")
        print(f"   Action stack var: {self.action_stack_var}")
        print(f"   Button/movieclip: {self.button_movieclip}")
        print(f"   Buffer sound:     {self.buffer_sound}")

        print(f"   Load addr:        0x{self.load_addr:08x}")
        print(f"   Binary size:      0x{self.binary_size:08x}")
        print(f"   MP3 offset:       0x{self.mp3_offset:08x}")
        print(f"   MP3 length:       0x{self.mp3_length:08x}")
        print()

        decrypted = decrypt_header(self.data[self.idx:self.idx+0x20])
        self.idx += 0x20

        print()
        self.frame_idx, self.image_idx, self.action_idx, self.movie_idx, self.button_idx, self.button_cond_idx = struct.unpack("<LLLLLL", decrypted[0x8:])
        print(f"  Frame table:       0x{self.frame_idx:08x}")
        print(f"  Image table:       0x{self.image_idx:08x}")
        print(f"  Action table:      0x{self.action_idx:08x}")
        print(f"  Movie table:       0x{self.movie_idx:08x}")
        print(f"  Button table:      0x{self.button_idx:08x}")
        print(f"  Button cond table: 0x{self.button_cond_idx:08x}")

        # Cursor?
        self.cursor_width, self.cursor_height = struct.unpack("<HH", self.data[self.idx:self.idx+0x4])
        self.idx += 0x4
        cursor_size = 2*self.cursor_width*self.cursor_height
        self.cursor = bytes(self.data[self.idx:self.idx+cursor_size])
        self.idx += cursor_size
        self.sound_table = self.idx

    def _get_str(self, offset):
        s = ''
        while offset < len(self.data):
            if self.data[offset] == 0x0:
                break
            s += chr(self.data[offset])
            offset += 1
        return s

    def disassemble_actions(self, out_dir):
        i = self.base + self.action_idx
        self.actions = []
        while i < len(self.data) - 8:
            opcode, payload = struct.unpack("<LL", self.data[i:i+8])
            try:
                act = Action(opcode)
            except ValueError:
                break
            if payload == 0x0 or act == Action.End:
                payload = None
            else:
                payload_idx = self.base + payload
                if payload_idx < len(self.data):
                    if act in (Action.If, Action.GotoFrame, Action.Jump):
                        payload, = struct.unpack("<h", self.data[payload_idx:payload_idx+2])
                    else:
                        payload = self._get_str(payload_idx)
            self.actions.append((act, payload))
            i += 8

        with open(f"{out_dir}/actions.txt", "w") as f:
            for act, payload in self.actions:
                if payload is None:
                    fmt_payload = ''
                elif isinstance(payload, int):
                    fmt_payload = f' {payload:08x}'
                else:
                    fmt_payload = f' {payload}'
                print(f"{act.name:16}{fmt_payload}", file=f)

    def extract_images(self, out_dir):
        i = self.base + self.image_idx
        Path(f"{out_dir}/images").mkdir(exist_ok=True)
        index = 0
        while i < len(self.data) - 4 and i != (self.base + self.movie_idx):
            img_offset, = struct.unpack("<L", self.data[i:i+4])
            if img_offset == 0xFFFFFFFF:
                break
            img_width, img_height, img_size = struct.unpack("<HHL", self.data[self.base+img_offset:self.base+img_offset+8])
            with open(f"{out_dir}/images/{index+1}.bin", "wb") as f:
                f.write(self.data[self.base+img_offset:self.base+img_offset+img_size+8]) # +8 to include header
            img = decode_image(self.data[self.base+img_offset:self.base+img_offset+img_size+8])
            img.save(f"{out_dir}/images/{index+1}.png", "PNG")
            index += 1
            i += 4

    def extract_frame(self, offset):
        objects = []
        i = self.base + offset
        while i < len(self.data) - 0x10:
            obj_type, index, x, y, depth, resv, name = struct.unpack("<HHHHHHL", self.data[i:i+0x10])
            if obj_type == 0x0000 or obj_type == 0xFFFF:
                break
            obj_type = ObjectType(obj_type)
            if name != 0x0000:
                name = self._get_str(self.base + name)
            else:
                name = None
            objects.append((obj_type, index, x, y, depth, name))
            i += 0x10
        return objects

    def extract_frames(self, out_dir):
        i = self.base + self.frame_idx
        self.frames = []
        with open(f"{out_dir}/frames.txt", "w") as f:
            while i < len(self.data) - 0x04:
                offset, = struct.unpack("<L", self.data[i:i+4])
                if offset == 0x0 or offset > len(self.data):
                    break
                objects = self.extract_frame(offset)
                self.frames.append(objects)
                print(f"Frame {len(self.frames)}", file=f)
                for obj_type, index, x, y, depth, name in objects:
                    print(f"  {obj_type.name:6} {index:5} X={x:3} Y={y:3} depth={depth:3} {name or ''}", file=f)
                print("", file=f)
                i += 4

    def decompile_actions(self, out_dir):
        with open(f"{out_dir}/frame_actions.txt", "w") as f:
            for i, frame in enumerate(self.frames):
                for obj_type, index, x, y, depth, name in frame:
                    if obj_type == ObjectType.Action:
                        decompile(f, self.actions, index, f"frame{i+1}_act{index}")
        with open(f"{out_dir}/movie_actions.txt", "w") as f:
            for i, movie in sorted(self.movies.items(), key=lambda x: x[0]):
                for index, x, y, event, u2, u3 in movie:
                    if event != 0:
                        decompile(f, self.actions, event, f"movie{i}_act{event}")

    def extract_movie(self, index):
        idx_ptr = self.base + self.movie_idx + (4 * (index - 1))
        ptr, = struct.unpack("<L", self.data[idx_ptr:idx_ptr+4])
        ptr += self.base
        items = []
        while ptr < len(self.data) - 0x0C:
            obj = struct.unpack("<HhhHHh", self.data[ptr:ptr+0xC])
            if obj[0] == 0xFFFF or obj[0] == 0x0000:
                break
            items.append(obj)
            ptr += 0xC
        return items

    def extract_movies(self, out_dir):
        self.movies = {}
        movie_indices = set()
        for frame in self.frames:
            for obj_type, index, x, y, depth, name in frame:
                if obj_type == ObjectType.Movie:
                    movie_indices.add(index)
        with open(f"{out_dir}/movies.txt", "w") as f:
            for i in sorted(movie_indices):
                print(f"Movie {i}: ", file=f)
                movie_frames = self.extract_movie(i)
                self.movies[i] = movie_frames
                for index, x, y, event, sound, u3 in movie_frames:
                    print(f"    {index:5} X={x:3} Y={y:3} {event:5} {sound:5} {u3:5}", file=f)
                print("", file=f)

    def extract_sound(self, idx, out_dir):
        table_idx = self.sound_table + (idx - 1) * 4
        ptr, = struct.unpack("<L", self.data[table_idx:table_idx+4])
        print(f"Sound {idx:2d}: 0x{ptr:08x}")
        flags = ptr & 0xF0000000
        addr = ptr & 0x0FFFFFFF
        if flags == 0xF0000000: # MP3 audio
            # MP3 format
            begin = self.base + self.mp3_offset + addr
            size, unk = struct.unpack("<LH", self.data[begin:begin+6])
            begin += 6
            with open(f"{out_dir}/sound/{idx}.mp3", "wb") as f:
                f.write(self.data[begin:begin+size])
        elif flags == 0x00000000: # raw samples
            # 22050Hz?, 16-bit, big endian, mono?
            begin = self.base + addr
            size, = struct.unpack("<L", self.data[begin:begin+4])
            begin += 4
            with open(f"{out_dir}/sound/{idx}.bin", "wb") as f:
                f.write(self.data[begin:begin+size])

    def extract_sounds(self, out_dir):
        Path(f"{out_dir}/sound").mkdir(exist_ok=True)
        sound_indices = set()
        for movie_frames in self.movies.values():
            for index, x, y, event, sound, u3 in movie_frames:
                if sound != 0:
                    sound_indices.add(sound & 0xFF)
        for sound in sorted(sound_indices):
            self.extract_sound(sound, out_dir)

    def decompile_button(self, button, f):
        print(f"# Button {button}", file=f)
        btn_table_idx = self.base + self.button_idx + (button - 1) * 4
        ptr, = struct.unpack("<L", self.data[btn_table_idx:btn_table_idx+4])
        ptr += self.base
        for i in range(4):
            image, x, y, depth = struct.unpack("<HHHH", self.data[ptr:ptr+8])
            print(f"# Image {image:4} X={x:3} Y={y:3} depth={depth:3}", file=f)
            ptr += 0x8
        cond_table_idx = self.base + self.button_cond_idx + (button - 1) * 4
        ptr, = struct.unpack("<L", self.data[cond_table_idx:cond_table_idx+4])
        ptr += self.base
        total_act_len, = struct.unpack("<H", self.data[ptr:ptr+2])
        ptr += 2
        i = 0
        while i < total_act_len:
            keycode, act_len, event = struct.unpack("<HHH", self.data[ptr:ptr+6])
            decompile(f, self.actions, event, f"button{button}_keycode{keycode:04x}_act{event}")
            i += act_len # what is this really??
            ptr += 0x6
        print("", file=f)

    def extract_buttons(self, out_dir):
        button_indices = set()
        for frame in self.frames:
            for obj_type, index, x, y, depth, name in frame:
                if obj_type == ObjectType.Button:
                    button_indices.add(index)
        with open(f"{out_dir}/button_actions.txt", "w") as f:
            for button in button_indices:
                self.decompile_button(button, f)

    def run(self, out_dir):
        Path(out_dir).mkdir(exist_ok=True)
        self.skip_thumbnail()
        self.find_header()
        self.process_header()
        self.disassemble_actions(out_dir)
        self.extract_frames(out_dir)
        self.extract_movies(out_dir)
        self.decompile_actions(out_dir)
        self.extract_buttons(out_dir)
        self.extract_images(out_dir)
        self.extract_sounds(out_dir)

if __name__ == '__main__':
    with open(sys.argv[1], 'rb') as f:
        Native32Reader(f).run(sys.argv[2])
