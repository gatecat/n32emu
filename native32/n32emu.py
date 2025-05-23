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

    _visible: bool = True
    _playing: bool = True
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
        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Movie:
                assert obj.name is not None # TODO: does this ever exist?
                if obj.name in self.movies:
                    # Don't add/reset movies that already exist
                    continue
                self.movies[obj.name] = MovieState(movie=obj.index, x=obj.x, y=obj.y, depth=obj.depth)
        # TODO: button, sound, action

    def draw_frame(self, screen):
        drawlist = []
        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Image:
                drawlist.append(DrawEntry(obj.index, obj.x, obj.y, obj.depth))
        for movie in self.movies.values():
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
            for obj in self.cur_frame:
                if obj.obj_type == ObjectType.Action:
                    self.vm.run(obj.index, "")

        for movie_name, movie in self.movies.items():
            movie_frames = self.r.get_movie(movie.movie)
            if movie._next_frame is None and movie._playing and movie.frame < len(movie_frames) - 1:
                # todo: not if sound playing
                movie._next_frame = movie.frame + 1
            if movie._next_frame is not None:
                movie.frame = movie._next_frame
                movie._next_frame = None
                # todo: sound
                if movie_frames[movie.frame].action != 0:
                    self.vm.run(movie_frames[movie.frame].action, movie_name)
    def stop(self, target):
        if target == "":
            self._playing = False
        else:
            self.movies[target]._playing = False

    def play(self, target):
        if target == "":
            self._playing = True
        else:
            self.movies[target]._playing = False

    def get_frame(self, target):
        if target == "":
            return self.frame
        else:
            return self.movies[target].frame

    def goto_frame(self, target, frame):
        if target == "":
            self._next_frame = frame
        else:
            self.movies[target]._next_frame = frame

    def stop_sounds(self, target):
        pass

    def call(self, target):
        frame = self.r.get_frame(target)
        for obj in frame:
            if obj.obj_type == ObjectType.Action:
                self.vm.run(obj.index, "")

    def get_property(self, target, prop):
        m = self.movies[target]
        if prop == ActionProp.x:
            return m.x
        elif prop == ActionProp.y:
            return m.y
        elif prop == ActionProp.visible:
            return int(m._visible)
        elif prop == ActionProp.currentframe:
            return m.frame
        elif prop == ActionProp.totalframes:
            return len(self.r.get_movie(m.movie))
        else:
            assert False, (target, prop)

    def set_property(self, target, prop, value):
        m = self.movies[target]
        if prop == ActionProp.x:
            m.x = int(value)
        elif prop == ActionProp.y:
            m.y = int(value)
        elif prop == ActionProp.visible:
            m._visible = bool(int(value))
        elif prop == ActionProp.currentframe:
            m._next_frame = int(value)
        else:
            assert False, (target, prop, value)

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((320, 240), flags=pygame.SCALED)
        clock = pygame.time.Clock()

        running = True
        while running:

            self.tick()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            screen.fill("black")
            self.draw_frame(screen)
            pygame.display.flip()

            clock.tick(30)

        pygame.quit()

def main():
    emu = N32Emu(sys.argv[1])
    emu.run()

if __name__ == '__main__':
    main()


