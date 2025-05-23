import sys
import pygame
from process_file import *
from dataclasses import dataclass
from actionvm import ActionVM, ActionProp

@dataclass
class MovieState:
    movie: int
    x: int
    y: int
    depth: int
    frame: int = 0

    _cloned_sprite: bool = False # this stops it being deleted when we load a new frame
    _visible: bool = True
    _playing: bool = False
    _next_frame: int|None = 0

@dataclass
class DrawEntry:
    image: int
    x: int
    y: int
    depth: int

class N32Emu:
    def __init__(self, filename):
        with open(filename, "rb") as f:
            self.r = Native32Reader(f)
        self.r.init()
        self.movies = {}
        self._playing = True
        self._next_frame = 1
        self.frame = 0
        self.vm = ActionVM(self)

    def load_frame(self, i):
        self.cur_frame = self.r.get_frame(i)
        # Update movie list
        frame_movies = set()
        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Movie:
                assert obj.name is not None # TODO: does this ever exist?
                frame_movies.add(obj.name)
                if obj.name in self.movies:
                    # Don't add/reset movies that already exist
                    continue
                self.movies[obj.name] = MovieState(movie=obj.index, x=obj.x, y=obj.y, depth=obj.depth)
        delete_movies = []
        for movie_name, movie in self.movies.items():
            if movie_name not in frame_movies and not movie._cloned_sprite:
                delete_movies.append(movie_name)
        for movie in delete_movies:
            del self.movies[movie]
        # TODO: button, sound

    def draw_frame(self, screen):
        drawlist = []
        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Image:
                drawlist.append(DrawEntry(obj.index, obj.x, obj.y, obj.depth))
        for movie in self.movies.values():
            if not movie._visible:
                continue
            frame = self.r.get_movie(movie.movie)[movie.frame]
            drawlist.append(DrawEntry(frame.image, movie.x + frame.x, movie.y + frame.y, movie.depth))

        drawlist.sort(key = lambda x: x.depth)
        for d in drawlist:
            img = self.r.get_image(d.image)
            screen.blit(img, (d.x, d.y))

    def tick(self):
        if self._next_frame is None and self._playing:
            self._next_frame = self.frame + 1
        if self._next_frame is not None:
            self.frame = self._next_frame
            self._next_frame = None
            self.load_frame(self.frame)

        for movie_name, movie in self.movies.items():
            movie_frames = self.r.get_movie(movie.movie)
            if movie._next_frame is None and movie._playing and movie.frame < len(movie_frames) - 1:
                # todo: not if sound playing
                movie._next_frame = movie.frame + 1
            if movie._next_frame is not None:
                if movie._next_frame == -1:
                    movie._next_frame = 0
                if movie._next_frame < len(movie_frames):
                    movie.frame = movie._next_frame
                    movie._next_frame = None
                    # todo: sound
                    if movie_frames[movie.frame].action != 0:
                        self.vm.run(movie_frames[movie.frame].action, movie_name)


        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Action:
                self.vm.run(obj.index, "")

        # Handle "buttons"
        keys = pygame.key.get_pressed()
        key_map = {
            0x0200: pygame.K_LEFT,
            0x0400: pygame.K_RIGHT,
            0x1c00: pygame.K_UP,
            0x1e00: pygame.K_DOWN,
            0x4000: pygame.K_z,
            0x8800: pygame.K_x,
        }
        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Button:
                events = self.r.get_button_events(obj.index)
                for keycode, action in events:
                    if keycode in key_map and keys[key_map[keycode]]:
                        self.vm.run(action, "")

    def stop(self, target):
        print(f"   stop({target})")
        if target == "":
            self._playing = False
        else:
            self.movies[target]._playing = False

    def play(self, target):
        print(f"   play({target})")
        if target == "":
            self._playing = True
        else:
            self.movies[target]._playing = True

    def get_frame(self, target):
        if target == "":
            return self.frame
        else:
            return self.movies[target].frame + 1

    def goto_frame(self, target, frame):
        print(f"   goto_frame({target}, {frame})")
        if target == "":
            self._next_frame = frame
        else:
            self.movies[target]._next_frame = frame - 1

    def stop_sounds(self, target):
        pass

    def call(self, target):
        frame = self.r.get_frame(target)
        for obj in frame:
            if obj.obj_type == ObjectType.Action:
                self.vm.run(obj.index, "")

    def get_property(self, target, prop):
        if target not in self.movies:
            return 0
        m = self.movies[target]
        if prop == ActionProp.x:
            return m.x
        elif prop == ActionProp.y:
            return m.y
        elif prop == ActionProp.visible:
            return int(m._visible)
        elif prop == ActionProp.currentframe:
            return m.frame + 1
        elif prop == ActionProp.totalframes:
            return len(self.r.get_movie(m.movie))
        elif prop == ActionProp.name:
            return target
        else:
            assert False, (target, prop)

    def set_property(self, target, prop, value):
        if target not in self.movies:
            return
        m = self.movies[target]
        if prop == ActionProp.x:
            m.x = int(float(value))
        elif prop == ActionProp.y:
            m.y = int(float(value))
        elif prop == ActionProp.visible:
            m._visible = bool(float(value))
        elif prop == ActionProp.currentframe:
            m._next_frame = int(float(value))
        elif prop == ActionProp.name:
            self.movies[value] = m
            del self.movies[target]
        else:
            assert False, (target, prop, value)

    def clone_sprite(self, src, dest, depth):
        orig = self.movies[src]
        self.movies[dest] = MovieState(movie=orig.movie, x=orig.x, y=orig.y, depth=depth,
            frame=-1, _visible=orig._visible, _playing=orig._playing, _next_frame=orig.frame,
            _cloned_sprite=True)
    def remove_sprite(self, name):
        if name in self.movies:
            del self.movies[name]

    def get_time(self):
        return self.time

    def run(self):
        pygame.init()
        pygame.display.set_caption("n32emu")
        screen = pygame.display.set_mode((320, 240), flags=pygame.SCALED)
        clock = pygame.time.Clock()
        self.time = 0

        running = True
        while running:
            print(f"frame={self.frame} next={self._next_frame}")
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.tick()

            screen.fill("black")
            self.draw_frame(screen)
            pygame.display.flip()

            clock.tick(30)
            self.time += 1000//30

        pygame.quit()

def main():
    emu = N32Emu(sys.argv[1])
    emu.run()

if __name__ == '__main__':
    main()


