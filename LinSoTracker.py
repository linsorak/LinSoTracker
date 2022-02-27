import os
import pygame
from Engine.MainMenu import MainMenu
from Tools.CoreService import CoreService


def main():
    core_service = CoreService()
    menu = MainMenu()
    dimension = menu.get_dimension()
    pygame.init()
    screen = pygame.display.set_mode(dimension)
    pygame.display.set_caption(core_service.get_window_title())
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Tahoma", 20)

    menu.initialization()
    pygame.display.set_icon(menu.get_icon())

    os.environ['SDL_VIDEO_CENTERED'] = '1'
    def update_fps():
        fps = str(int(clock.get_fps()))
        fps_text = font.render("FPS : {} - DEV TEST VERSION".format(fps), 1, pygame.Color("white"))
        return fps_text

    loop = True
    mouse_position = None
    while loop:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False

            if event.type == pygame.MOUSEMOTION:
                mouse_position = pygame.mouse.get_pos()
                menu.mouse_move(mouse_position)

            if event.type == pygame.MOUSEBUTTONUP: #and event.button == 1:
                menu.click(mouse_position, event.button)
                # tracker.click(mouse_position, event.button)

        clock.tick(30)
        menu.draw(screen)
        # tracker.draw(screen)

        screen.blit(update_fps(), (10, 0))
        pygame.display.update()

    pygame.quit()

if __name__ == '__main__':
    main()