# Example file showing a basic pygame "game loop"
import asyncio
import threading
import logging
from dataclasses import dataclass

import pygame

# pygame setup
pygame.init()
screen = pygame.display.set_mode((800, 800))
clock = pygame.time.Clock()
running = True

def prepare_image(file_name, scale, angle):
    img = pygame.image.load(file_name)
    img.convert()
    img = pygame.transform.rotozoom(img, angle, scale)

    img.set_colorkey("black")

    return img

class Console:
    def __init__(self, screen):
        self.x = 0
        self.y = 0
        self.width = screen.get_width()
        self.height = 100
        self.color = "white"
        self.text = ""
        self.font = pygame.font.SysFont(None, 22)
        self.screen = screen
        self.visible = True

    def hide(self):
        self.visible = False

    def show(self):
        self.visible = True

    def draw(self):
        if not self.visible:
            return

        # draw transparent background with alpha 128
        # pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height), 0, pygame.BLEND_RGBA_MULT)

        s = pygame.Surface((self.width, self.height))  # the size of your rect
        s.set_alpha(80)  # alpha level
        s.fill(self.color)  # this fills the entire surface
        screen.blit(s, (self.x, self.y))

        # pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

        text = self.font.render(self.text, True, "white")

        # draw transparent text
        text.set_alpha(190)
        screen.blit(text, (self.x + 10, self.y + 10))

    def log(self, text):
        self.text = text

    def update(self):
        pass

class Player:
    def __init__(self, screen, image_files, scale, angle):
        self.x = 0
        self.y = 0
        self.id = None

        self.screen = screen

        self.image_index = 0

        self.images = []
        for file_name in image_files:
            self.images.append(prepare_image(file_name, scale, angle))

        self.image = self.images[self.image_index]
        self.rect = self.image.get_rect()

    def draw(self):
        self.screen.blit(self.image, self.rect)

    def update(self):
        self.image_index += 1
        self.image_index %= len(self.images)

        self.image = self.images[self.image_index]

        self.rect.x = self.x
        self.rect.y = self.y

class Bullet:
    def __init__(self, screen, image_files, scale, angle):
        self.x = 0
        self.y = 0

        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        self.screen = screen

        self.width = 10
        self.height = 10
        self.color = "red"
        self.speed_x = 0
        self.speed_y = 0

        self.is_active = True

        self.image_index = 0

        self.images = []
        for file_name in image_files:
            self.images.append(prepare_image(file_name, scale, angle))

        self.image = self.images[self.image_index]
        self.rect = self.image.get_rect()

    def draw(self):
        if not self.is_active:
            return

        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))

    def update(self):

        self.x += self.speed_x
        self.y += self.speed_y

        if self.x < 0 or self.x > self.screen_width or self.y < 0 or self.y > self.screen_height:
            self.is_active = False
            return

        self.image_index += 1
        self.image_index %= len(self.images)

        self.image = self.images[self.image_index]

        self.rect.x = self.x
        self.rect.y = self.y

@dataclass
class EventsData:
    down_key: bool
    up_key: bool
    left_key: bool
    right_key: bool
    fire_key: bool

async def send_events(eventsData, writer):
    while running:
        move_x = -1 if eventsData.left_key else 1 if eventsData.right_key else 0
        move_y = -1 if eventsData.up_key else 1 if eventsData.down_key else 0
        fire = 1 if eventsData.fire_key else 0

        message = f"{move_x},{move_y},{fire}\n"

        writer.write(message.encode())
        await writer.drain()
        await asyncio.sleep(0.2)

        logging.info(f"send_events coroutine: sent {message}")

async def receive_events(player, other_players, reader):
    while running:
        message = await reader.readline()

        logging.info(f"message received: {message.decode()}")
        data_parts=message.decode().split(",")
        # print(data_parts)

        # while len(other_players) < len(data_parts) / 3:
        #     other_players.append(Player(screen, ["images/e-ship1.png", "images/e-ship2.png", "images/e-ship3.png"], 0.25, 0))
        ids = []
        for i in range(0, len(data_parts), 3):
            if data_parts[i] == "":
                continue
            player_id = int(data_parts[i])
            while len(other_players) <= player_id :
                other_players.append(Player(screen, ["images/e-ship1.png", "images/e-ship2.png", "images/e-ship3.png"], 0.25, 0))
                print(f"adding player {player_id}")
            ids.append(player_id)
            # print(f"player_id: {player_id}, len(other_players): {len(other_players)}")
        for i in range(0, len(data_parts), 3):
            if data_parts[i] == "":
                continue
            player_id = int(data_parts[i])
            if player_id == player.id:
                # print('updating player')
                player.x = float(data_parts[i+1])
                player.y = float(data_parts[i+2])
            else:
                # print(f"player_id: {player_id}, len(other_players): {len(other_players)}")
                other_players[player_id].x = float(data_parts[i+1])
                other_players[player_id].y = float(data_parts[i+2])
                other_players[player_id].id = player_id

        # remove players that are not in the list
        for player_o in other_players:
            if player_o.id not in ids and player_o.id != None:
                print(f"removing player {player_o.id}")
                other_players.remove(player_o)

async def data_exchange(player, eventsData, other_players):
    reader, writer = await asyncio.open_connection('localhost', 8888)

    initial_data = await reader.readline()
    logging.info(f"initial data received: {initial_data.decode()}")
    data_parts=initial_data.decode().split(":")
    player.id = int(data_parts[1])
    print(f"player id: {player.id}")

    send_events_task = asyncio.create_task(send_events(eventsData, writer))
    receive_events_task = asyncio.create_task(receive_events(player, other_players, reader))

    await asyncio.gather(send_events_task, receive_events_task)

    print("data_exchange coroutine finished")

def data_exchange_thread_func(player, eventsData, other_players):
    global running

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(data_exchange(player, eventsData, other_players))

    loop.close()

    print("data_exchange thread finished")

def main():
    global running

    other_players = []

    player = Player(screen, ["images/ship1.png", "images/ship2.png", "images/ship3.png"], 0.25, 0)
    console = Console(screen)

    eventsData = EventsData(False, False, False, False, False)

    # create data exchange thread
    data_exchange_thread = threading.Thread(target=data_exchange_thread_func, args=(player, eventsData, other_players))
    data_exchange_thread.start()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    eventsData.up_key = True
                elif event.key == pygame.K_DOWN:
                    eventsData.down_key = True
                elif event.key == pygame.K_LEFT:
                    eventsData.left_key = True
                elif event.key == pygame.K_RIGHT:
                    eventsData.right_key = True
                elif event.key == pygame.K_SPACE:
                    eventsData.fire_key = True
                    pass
                elif event.key == pygame.K_c:
                    if console.visible:
                        console.hide()
                    else:
                        console.show()

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    eventsData.up_key = False
                elif event.key == pygame.K_DOWN:
                    eventsData.down_key = False
                elif event.key == pygame.K_LEFT:
                    eventsData.left_key = False
                elif event.key == pygame.K_RIGHT:
                    eventsData.right_key = False
                elif event.key == pygame.K_SPACE:
                    eventsData.fire_key = False


        # fill the screen with a color to wipe away anything from last frame
        screen.fill("black")

        # draw other players
        # print(f"other players: {len(other_players)}")
        for other_player in other_players:
            if other_player.id is not None:
                # print(f"other player id: {other_player.id}")
                other_player.update()
                other_player.draw()

        if player.id is not None:
            # print(f"player id: {player.id}")
            player.update()
            player.draw()

        console.log(f"Player x: {int(player.x)}, y: {int(player.y)}")
        console.draw()

        # flip() the display to put your work on screen
        pygame.display.flip()

        clock.tick(60)  # limits FPS to 60

    data_exchange_thread.join()
    pygame.quit()

if __name__ == "__main__":
    format = "SRV: %(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.ERROR,
                        datefmt="%F-%H-%M-%S")

    main()