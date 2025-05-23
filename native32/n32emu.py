import sys
import pygame
from process_file import *
from dataclasses import dataclass

@dataclass
class MovieState:
    movie: int
    x: int
    y: int
    depth: int
    frame: int = 0

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

    def load_frame(self, i):
        self.cur_frame = self.r.get_frame(i)
        # Update movie list
        for obj in self.cur_frame:
            if obj.obj_type == ObjectType.Movie:
                assert obj.name is not None # TODO: does this ever exist?
                if obj.name in self.movies:
                    # Don't add/reset movies that already exist
                    continue
                self.movies[obj.name] = MovieState(movie=obj.index, x=obj.x, y=obj.y, depth=obj.depth, frame=0)

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

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((320, 240), flags=pygame.SCALED)
        clock = pygame.time.Clock()

        running = True

        self.load_frame(1)

        while running:
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


