import os

import pygame

from Engine.Tracker import Tracker
from Tools.CoreService import CoreService


def main():
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    tracker = Tracker(template_name="")
    core_service = CoreService()
    pygame.init()
    screen = pygame.display.set_mode((1000, 720))
    pygame.display.set_caption(core_service.get_window_title())
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Tahoma", 18)

    def update_fps():
        fps = str(int(clock.get_fps()))
        fps_text = font.render(fps, 1, pygame.Color("coral"))
        return fps_text

    loop = True
    mouse_position = None
    while loop:
        screen.fill((0, 0, 0))
        screen.blit(update_fps(), (10, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False

            if event.type == pygame.MOUSEMOTION:
                mouse_position = pygame.mouse.get_pos()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                pass

        clock.tick(30)
        pygame.display.update()

    pygame.quit()

if __name__ == '__main__':
    main()