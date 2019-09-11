import math
import random
import sys
import os
from itertools import chain

from pyglet.gl import *
from pyglet.window import key

import pybario

script_dir = os.path.dirname(__file__)


def pix_idx_to_pos(col, row, detector):
    height_scale = 0.35
    return (col + 3.) / 80 * detector.width * 0.965 - detector.width / 2, (row + 1.) / 336 * detector.height * height_scale - detector.height / 2


_MAX_HITS = 10  # maximum hits to visualize, new hits delete old
_MAX_TRACKS = 3  # maximum hits to visualize, new tracks are only drawn when old ones faded out
_COMBINE_N_READOUTS = 20
_CLEAR_COLOR = (0.87, 0.87, 0.87, 1)


class Hit(object):
    dx, dy = 1.5, 1.5

    def __init__(self, x, y):
        self.x = x - self.dx
        self.y = y + self.dy
        self.transparency = 100

    def update(self, dt):
        # Fade out hit
        self.transparency += dt * 50
        if self.transparency > 255:
            return False
        return True

    def draw(self):
        X, Y, Z = self.x + self.dx, self.y + self.dy, 3.
        alpha = 255 - int(self.transparency)
        pyglet.graphics.draw(4, GL_QUADS, ('v3f', (self.x, self.y, Z, X, self.y, Z, X, Y, Z, self.x, Y, Z)),
                             ('c4B', (255, 0, 0, alpha,
                                      255, 0, 0, alpha,
                                      255, 0, 0, alpha,
                                      255, 0, 0, alpha)))


class Track(object):
    dx, dy = 1.5, 1.5

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        direction = (p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2])
        position = p1
        self.track_start = (position[0] - 1000 * direction[0], position[1] - 1000 * direction[1], position[2] - 1000 * direction[2])
        self.track_stop = (position[0] + 1000 * direction[0], position[1] + 1000 * direction[1], position[2] + 1000 * direction[2])
        self.transparency = 100

    def update(self, dt):
        # Fade out hit
        self.transparency += dt * 1
        if self.transparency > 200:
            self.transparency = 200
        if self.transparency > 255:
            return False
        return True

    def draw(self):
        alpha = 255 - int(self.transparency)
        # Show track
        pyglet.graphics.draw(2, GL_LINES, ('v3f', (self.track_start[0], self.track_start[1], self.track_start[2],
                                                   self.track_stop[0], self.track_stop[1], self.track_stop[2])),
                             ('c4B', (0, 128, 187, alpha, 0, 128, 187, alpha)))
        # Show track hits too
        alpha = 255
        x, y = self.p1[0], self.p1[1]
        X, Y, Z = self.p1[0] + self.dx, self.p1[1] + self.dy, self.p1[2] + 3.
        pyglet.graphics.draw(4, GL_QUADS, ('v3f', (x, y, Z, X, y, Z, X, Y, Z, x, Y, Z)),
                             ('c4B', (255, 0, 0, alpha,
                                      255, 0, 0, alpha,
                                      255, 0, 0, alpha,
                                      255, 0, 0, alpha)))
        x, y = self.p2[0], self.p2[1]
        X, Y, Z = self.p2[0] + self.dx, self.p2[1] + self.dy, self.p2[2] + 3.
        pyglet.graphics.draw(4, GL_QUADS, ('v3f', (x, y, Z, X, y, Z, X, Y, Z, x, Y, Z)),
                             ('c4B', (255, 0, 0, alpha,
                                      255, 0, 0, alpha,
                                      255, 0, 0, alpha,
                                      255, 0, 0, alpha)))


class Module(object):
    ''' Single module of the telescope '''

    def __init__(self, x, y, z):
        detector_image = pyglet.image.load(os.path.join(script_dir, 'media', 'SC.png'))
        detector = pyglet.sprite.Sprite(detector_image, x=x, y=y, subpixel=True)
        detector.scale = 0.1
        detector.rotation = 180
        detector.x += detector.width / 2.
        detector.y += detector.height / 2.
        detector.z = z

        self.detector = detector
        self.hits = []

        pix_idc = [(0, 0), (0, 335), (79, 0), (79, 336)]
        for col, row in pix_idc:
            x, y = pix_idx_to_pos(col, row, detector)
            self.hits.append(Hit(x, y))

    def add_hits(self, hits):
        if not hits:
            return False
        added_hits = False
        for i, (col, row) in enumerate(hits):
            x, y = pix_idx_to_pos(col, row, self.detector)
            # Do not add existing hits
            for hit in self.hits:
                if abs(x - hit.x - hit.dx) < 0.1 and abs(y - (hit.y - hit.dy)) < 0.1:
                    break
            else:
                if len(self.hits) < _MAX_HITS:
                    self.hits.append(Hit(x, y))
                    added_hits = True
                elif i < _MAX_HITS:
                    self.hits.pop(0)
                    self.hits.append(Hit(x, y))
                    added_hits = True
                else:
                    break
        return added_hits

    def update(self, dt):
        for i in range(len(self.hits) - 1, -1, -1):
            if not self.hits[i].update(dt):
                del self.hits[i]

    def draw(self):
        glTranslatef(0., 0., self.detector.z)
        self.detector.draw()
        for hit in self.hits:
            hit.draw()
        glTranslatef(0., 0., -self.detector.z)


class Telescope(object):
    ''' Visualization of a pixel telesecope '''

    def __init__(self, x=0, y=0, z=0):
        self.rotation = 0  # telescope rotation
        self.rot_speed = 20

        self.modules = []
        self.modules.append(Module(x, y, 0))
        self.modules.append(Module(x, y, 40))

        self.tracks = []
        
        self.hit_sound = pyglet.media.load(os.path.join(script_dir, 'media', 'hit.wav'), streaming=False)
        self.track_sound = pyglet.media.load(os.path.join(script_dir, 'media', 'track.wav'), streaming=False)
        self.play_sounds = 0

    def add_module_hits(self, module_hits):
        has_hits = []
        for i, one_module_hits in enumerate(module_hits):
            if one_module_hits is not None:
                has_hits.append(self.modules[i].add_hits(one_module_hits))
            else:
                has_hits.append(False)
        if self.play_sounds > 1 and any(has_hits):
            self.hit_sound.play()
        # Print a track if all modules are hit in this readout
        # Only print one track candidate if many tracks are possible
        try:
            if all(has_hits):
                hit_1 = (self.modules[0].hits[-1].x, self.modules[0].hits[-1].y, self.modules[0].detector.z)
                hit_2 = (self.modules[1].hits[-1].x, self.modules[1].hits[-1].y, self.modules[1].detector.z)
                if len(self.tracks) < _MAX_TRACKS:
                    self.tracks.append(Track(hit_1, hit_2))
                else:
                    self.tracks.pop(0)
                    self.tracks.append(Track(hit_1, hit_2))
                glClearColor(0.95, 0.95, 0.95, 1)
                def reset_background(_):
                        glClearColor(*_CLEAR_COLOR)
                pyglet.clock.schedule_once(reset_background, 0.1)
                if self.play_sounds:
                    self.track_sound.play()
        except IndexError:
            pass

    def update(self, dt):
        self.rotation += dt * self.rot_speed
        if self.rotation > 360:
            self.rotation -= 360
        for m in self.modules:
            m.update(dt)
        for i in range(len(self.tracks) - 1, -1, -1):
            if not self.tracks[i].update(dt):
                del self.tracks[i]

    def draw(self):
        ''' Called for every frame '''
        glRotatef(self.rotation, 0, 0, 1)  # rotate telescope
        for m in self.modules:
            m.draw()
        for track in self.tracks:
            track.draw()
        glRotatef(-self.rotation, 0, 0, 1)
        
    def reset(self):
        self.tracks = []
        for m in self.modules:
            m.hits = []
            
    def add_mc_track(self):
        for m in self.modules:
            m.add_hits([(random.randint(1, 80), random.randint(1, 336))])
        hit_1 = (self.modules[0].hits[-1].x, self.modules[0].hits[-1].y, self.modules[0].detector.z)
        hit_2 = (self.modules[1].hits[-1].x, self.modules[1].hits[-1].y, self.modules[1].detector.z)
        self.tracks.append(Track(hit_1, hit_2))

class Camera(object):
    ''' 3d camera movements '''

    def __init__(self, pos=[6, -120, 160], rot=[40, 0]):
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


class App(pyglet.window.Window):
    ''' 3d application window'''

    def __init__(self, *args, **kwargs):
        if sys.version_info[0] < 3:
            super(App, self).__init__(*args, **kwargs)
        else:
            super().__init__(*args, **kwargs)

        self.keys = key.KeyStateHandler()
        self.push_handlers(self.keys)
        pyglet.clock.schedule(self.update)

        self.telescope = Telescope()
        self.camera = Camera()
        self.io = pybario.IO(addresses=['tcp://127.0.0.1:5678', 'tcp://127.0.0.1:5679'], max_hits=_MAX_HITS)

        # Interface
        self.fps = pyglet.window.FPSDisplay(window=self)
        self.fps.label.font_size = 12
        # Legend
        self.text = pyglet.text.Label("Pixeltreffer", font_name="Arial", font_size=40, width=0.1 * self.width, x=self.width + 50, y=0.85*self.height,
                                      anchor_x='left', anchor_y='center', color=(255, 0, 0, 220))
        self.text_2 = pyglet.text.Label("Teilchenspuren", font_name="Arial", font_size=40, width=0.1 * self.width, x=self.width + 50, y=0.85*self.height - 100,
                                        anchor_x='left', anchor_y='center', color=(0, 128, 187, 220))

        self.logo = pyglet.sprite.Sprite(pyglet.image.load(os.path.join(script_dir, 'media', 'Silab.png')), x=self.width * 0.98, y=self.height * 0.98, subpixel=True)
        self.logo.scale = 0.2

        self.sound_logo = pyglet.sprite.Sprite(pyglet.image.load(os.path.join(script_dir, 'media', 'sound_off.png')), x=self.width * 0.98, y=self.height * 0.02, subpixel=True)
        self.sound_logo.scale = 0.2
        #self.sound_logo.x -= self.sound_logo.width
        #self.sound_logo.y += self.sound_logo.height
        self.logo.x = self.width * 0.98 - self.logo.width
        self.logo.y = self.height * 0.98 - self.logo.height
        self.text.x = self.width * 0.6
        self.text_2.x = self.width * 0.6
        self.sound_logo.x = self.width * 0.98 - self.sound_logo.width
        self.sound_logo.y = self.sound_logo.height
        # Options
        self.show_logo = True
        self.pause = False
        
        self.n_ro = 0
        self.mh =  [None, None]

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
            self.telescope.rot_speed += 10
        elif KEY == key.MINUS:
            self.telescope.rot_speed -= 10
        elif KEY == key.F or (KEY == key.ENTER and MOD == key.MOD_CTRL):
            self.set_fullscreen(not self._fullscreen)
        elif KEY == key.L:
            self.logo.visible = not self.logo.visible
            self.sound_logo.visible = self.logo.visible
        elif KEY == key.X:
            self.telescope.play_sounds += 1
            if self.telescope.play_sounds > 2:
                self.telescope.play_sounds = 0
            if self.telescope.play_sounds:
                self.sound_logo.image = pyglet.image.load(os.path.join(script_dir, 'media', 'sound.png') if self.telescope.play_sounds > 1 else os.path.join(script_dir, 'media', 'sound_silent.png'))
            else:
                self.sound_logo.image = pyglet.image.load(os.path.join(script_dir, 'media', 'sound_off.png'))
        elif KEY == key.P:
            self.pause = not self.pause
        elif KEY == key.R:
            self.telescope.reset()
        elif KEY == key.SPACE:
            self.telescope.add_mc_track()

    def update(self, dt):
        self.n_ro = self.n_ro + 1
        mh = self.io.get_module_hits()
        
        if not self.pause:
            if mh[0]:
                if self.mh[0] is None:
                    self.mh[0] = mh[0]
                else:
                    self.mh[0].extend(mh[0])
            if mh[1]:
                if self.mh[1] is None:
                    self.mh[1] = mh[1]
                else:
                    self.mh[1].extend(mh[1])
            if self.n_ro >= _COMBINE_N_READOUTS:
                self.n_ro = 0
                self.telescope.add_module_hits(self.mh)
                self.mh = [None, None]
            self.camera.update(dt, self.keys)
            self.telescope.update(dt)

    def draw_legend(self):
        glMatrixMode(gl.GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        self.logo.draw()
        self.text.draw()
        self.text_2.draw()
        self.sound_logo.draw()
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def on_draw(self):
        self.clear()
        self.set3d()
        self.draw_legend()
        self.fps.draw()
        self.push(self.camera.pos, self.camera.rot)
        self.telescope.draw()
        glPopMatrix()


if __name__ == '__main__':
    window = App(caption='Pixel detector model', resizable=True, fullscreen=True)
    # 3d settings
    glClearColor(*_CLEAR_COLOR)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_DONT_CARE)
    glLineWidth(5)
    glEnable(GL_BLEND)  # transparency
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)  # transparency
    glEnable(GL_CULL_FACE)

    pyglet.app.run()
