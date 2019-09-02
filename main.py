import sys

from pyglet.gl import *
from pyglet.window import key
import math


class Telescope(object):

    def __init__(self, x=0, y=0, z=0):
        self.rotation = 0
        self.batch = pyglet.graphics.Batch()

        self.detectors = []
        self.detectors.append(self.add_detector(x, y, 0))
        self.detectors.append(self.add_detector(x, y, 2))

    def add_detector(self, x, y, z):
        module_image = pyglet.image.load('DC.png')
        module = pyglet.sprite.Sprite(module_image, x=x, y=y)
        module.scale = 0.01
        module.rotation = 180
        module.x += module.width / 2
        module.y += module.height / 2
        module.z = z
        return module
#         # Quarder with texture
#         def get_tex(self, f):
#             tex = pyglet.image.load(f).get_texture()
#             glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
#             glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
#             return pyglet.graphics.TextureGroup(tex)
#         self.top = self.get_tex('grass_top.png')
#         self.side = self.get_tex('grass_side.png')
#         self.bottom = self.get_tex('dirt.png')
#         dx, dy, dz = 1, 0.1, 1
#         X, Y, Z = x + dx, y + dy, z + dz
#
#         tex_coords = ('t2f', (0, 0, 1, 0, 1, 1, 0, 1))
#
#         self.batch.add(4, GL_QUADS, self.side, ('v3f', (X, y, z, x, y, z, x, Y, z, X, Y, z)), tex_coords)  # back
#         self.batch.add(4, GL_QUADS, self.side, ('v3f', (x, y, Z, X, y, Z, X, Y, Z, x, Y, Z)), tex_coords)  # front
#
#         self.batch.add(4, GL_QUADS, self.side, ('v3f', (x, y, z, x, y, Z, x, Y, Z, x, Y, z)), tex_coords)  # left
#         self.batch.add(4, GL_QUADS, self.side, ('v3f', (X, y, Z, X, y, z, X, Y, z, X, Y, Z)), tex_coords)  # right
#
#         self.batch.add(4, GL_QUADS, self.bottom, ('v3f', (x, y, z, X, y, z, X, y, Z, x, y, Z)), tex_coords)  # bottom
#         self.batch.add(4, GL_QUADS, self.top, ('v3f', (x, Y, Z, X, Y, Z, X, Y, z, x, Y, z)), tex_coords)  # top

    def draw(self):
        glRotatef(self.rotation, 0, 0, 1)
        for det in self.detectors:
            glTranslatef(0., 0., det.z)
            det.draw()
            glTranslatef(0., 0., -det.z)
        glRotatef(-self.rotation, 0, 0, 1)


class Camera(object):

    def __init__(self, pos=[0, -6, 8], rot=[40, 0]):
        self.init_pos = pos
        self.init_rot = rot
        self.pos = list(self.init_pos)
        self.rot = list(self.init_rot)

    def reset(self):
        self.pos = list(self.init_pos)
        self.rot = list(self.init_rot)

    def mouse_motion(self, dx, dy):
        dx /= 8
        dy /= 8
        self.rot[0] += dy
        self.rot[1] -= dx
        if self.rot[0] > 90:
            self.rot[0] = 90
        elif self.rot[0] < -90:
            self.rot[0] = -90

    def update(self, dt, keys):
        s = dt * 10
        rotY = -self.rot[1] / 180 * math.pi
        dx, dz = s * math.sin(rotY), s * math.cos(rotY)
        if keys[key.Q]:
            self.pos[0] += dx
            self.pos[2] -= dz
        if keys[key.E]:
            self.pos[0] -= dx
            self.pos[2] += dz
        if keys[key.A]:
            self.pos[0] -= dz
            self.pos[2] -= dx
        if keys[key.D]:
            self.pos[0] += dz
            self.pos[2] += dx
        if keys[key.S]:
            self.pos[1] -= s
        if keys[key.W]:
            self.pos[1] += s
        if keys[key.SPACE]:
            self.reset()


class Window(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        if sys.version_info[0] < 3:
            super(Window, self).__init__(*args, **kwargs)
        else:
            super().__init__(*args, **kwargs)
        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)

        self.rot_speed = 0
        self.telescope = Telescope()
        self.camera = Camera()

        self.text = pyglet.text.Label("Play", font_name="Arial", font_size=32, x=10, y=10, anchor_x='center', anchor_y='center',
                                      color=(255, 0, 255, 100))

    def push(self, pos, rot):
        glPushMatrix()
        glRotatef(-rot[0], 1, 0, 0)
        glRotatef(-rot[1], 0, 1, 0)
        glTranslatef(-pos[0], -pos[1], -pos[2],)

    def Projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

    def Model(self):
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set2d(self):
        self.Projection()
        gluOrtho2D(0, self.width, 0, self.height)
        self.Model()

    def set3d(self):
        self.Projection()
        gluPerspective(70, self.width / self.height, 0.05, 1000)
        self.Model()

    def setLock(self, state):
        self.lock = state
        self.set_exclusive_mouse(state)

    lock = False
    mouse_lock = property(lambda self: self.lock, setLock)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.mouse_lock:
            self.camera.mouse_motion(dx, dy)

    def on_key_press(self, KEY, MOD):
        if KEY == key.ESCAPE:
            self.close()
        elif KEY == key.M:
            self.mouse_lock = not self.mouse_lock
        elif KEY == key.PLUS:
            self.rot_speed += 10
        elif KEY == key.MINUS:
            self.rot_speed -= 10
        elif KEY == key.F:
            window.set_fullscreen(not window._fullscreen)

    def update(self, dt):
        self.camera.update(dt, self.keys)
        self.telescope.rotation += dt * self.rot_speed
        if self.telescope.rotation > 360:
            self.telescope.rotation -= 360

    def on_draw(self):
        self.clear()
        self.set3d()
        self.push(self.camera.pos, self.camera.rot)
        self.telescope.draw()
        # self.text.draw()
        glPopMatrix()


if __name__ == '__main__':
    window = Window(width=1024, height=786, caption='Telescope', resizable=True)
    glClearColor(0.9, 0.9, 0.9, 1)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_DONT_CARE)
    glEnable(GL_BLEND)  # transparency
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # transparency
    glEnable(GL_CULL_FACE)
    pyglet.app.run()