"""Real OpenGL 3D renderer with two first-person viewports.

No prerecorded 2D fighter sprites: opponent, ring, gloves and arena are
drawn as depth-tested 3D primitives, once per player camera.
"""
from __future__ import annotations

import math
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *

WIDTH, HEIGHT = 1280, 720
CYAN = (0.15, 0.66, 0.98)
CORAL = (0.98, 0.28, 0.34)


def material(rgb, alpha=1.0):
    glColor4f(*rgb, alpha)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, (*rgb, alpha))


def box(x, y, z, w, h, d, color):
    material(color)
    glPushMatrix()
    glTranslatef(x, y, z)
    glScalef(w, h, d)
    glBegin(GL_QUADS)
    for normal, verts in (
        ((0, 0, 1), [(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]),
        ((0, 0,-1), [(.5,-.5,-.5),(-.5,-.5,-.5),(-.5,.5,-.5),(.5,.5,-.5)]),
        ((0, 1, 0), [(-.5,.5,.5),(.5,.5,.5),(.5,.5,-.5),(-.5,.5,-.5)]),
        ((0,-1, 0), [(-.5,-.5,-.5),(.5,-.5,-.5),(.5,-.5,.5),(-.5,-.5,.5)]),
        ((1, 0, 0), [(.5,-.5,.5),(.5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5)]),
        ((-1,0, 0), [(-.5,-.5,-.5),(-.5,-.5,.5),(-.5,.5,.5),(-.5,.5,-.5)]),
    ):
        glNormal3f(*normal)
        for v in verts:
            glVertex3f(*v)
    glEnd()
    glPopMatrix()


class Scene:
    def __init__(self, width=WIDTH, height=HEIGHT):
        self.width, self.height = width, height
        self.quadric = gluNewQuadric()
        gluQuadricNormals(self.quadric, GLU_SMOOTH)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (1.0, 4.0, 3.0, 0.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.96, 0.96, 1.0, 1.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (0.24, 0.24, 0.28, 1.0))
        glShadeModel(GL_SMOOTH)
        glClearColor(.045, .060, .092, 1.0)
        self.hud_texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.hud_texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        self.font_big = pygame.font.SysFont("arial", 36, bold=True)
        self.font_small = pygame.font.SysFont("arial", 21, bold=True)
        self.font_tiny = pygame.font.SysFont("arial", 16, bold=True)
        self.time = 0.0

    def close(self):
        glDeleteTextures([self.hud_texture])
        gluDeleteQuadric(self.quadric)

    def sphere(self, p, radius, color, slices=18):
        material(color)
        glPushMatrix()
        glTranslatef(*p)
        gluSphere(self.quadric, radius, slices, 12)
        glPopMatrix()

    def segment(self, a, b, radius, color):
        ax, ay, az = a
        bx, by, bz = b
        vx, vy, vz = bx-ax, by-ay, bz-az
        length = math.sqrt(vx*vx + vy*vy + vz*vz)
        if length < 0.001:
            return
        material(color)
        glPushMatrix()
        glTranslatef(ax, ay, az)
        # GLU cylinder axis is +Z.
        glRotatef(math.degrees(math.acos(max(-1.0,min(1.0,vz/length)))),
                  -vy, vx, 0.0) if abs(vz/length) < .9999 else glRotatef(180 if vz < 0 else 0, 1, 0, 0)
        gluCylinder(self.quadric, radius, radius, length, 12, 1)
        glPopMatrix()

    def arena(self):
        box(0, -.08, -4.0, 13, .15, 13, (.17, .23, .32))
        box(0, -.004, -4.0, 9, .035, 9, (.74,.79,.84))
        # stylized blue center circle
        self.sphere((0,-.12,-4), 1.35, (.15, .22, .38), 24)
        for x in (-4.45,4.45):
            for z in (-8.4,.4):
                box(x, 1.45, z, .14, 2.9, .14, (.23,.25,.34))
        # ring ropes, both sides and far wall
        colors = [(0.83,.23,.30), (.94,.94,.96), (.17,.45,.88)]
        for y,c in zip((.80,1.18,1.56),colors):
            for x in (-4.44,4.44):
                self.segment((x,y,.4),(x,y,-8.4),.033,c)
            for z in (-8.4,.4):
                self.segment((-4.44,y,z),(4.44,y,z),.033,c)
        # arena environment
        for x in (-6.2, 6.2):
            for z in (-10.0, 2.0):
                self.segment((x,0,z),(x,3.6,z), .13, (.20,.26,.32))
                self.sphere((x,3.6,z),.25,(.96,.85,.48))

    def opponent(self, color, guard=False, attack=0.0, flash=0.0, lean=0.0):
        glPushMatrix()
        glTranslatef(lean*.40, 0, -3.85)
        if flash > 0:
            color = (.99, .86, .36)
        skin = (.66,.43,.31)
        shorts = (.16,.18,.25)
        # torso and head
        box(0,1.45,0,.92,1.02,.46,color)
        box(0,.94,0,.92,.27,.49,shorts)
        self.sphere((0,2.19,0),.33,skin)
        box(0,2.43,-.055,.53,.10,.51,shorts)
        # neck
        self.segment((0,1.9,0),(0,2.02,0),.15,skin)
        # legs
        for s in (-1,1):
            x=.26*s
            self.segment((x,.87,0),(x*.98,.45,.08),.16,shorts)
            self.segment((x*.98,.45,.08),(x*1.1,.10,-.08),.14,skin)
            box(x*1.1,.08,-.22,.27,.14,.47,shorts)
        # arms with gloves
        for s in (-1,1):
            shoulder=(.52*s,1.83,0)
            elbow=(.64*s,1.58,-.18)
            glove=(.31*s,2.03,-.47) if guard else (.63*s,1.82,-.45)
            if attack > 0 and s == 1:
                glove=(.28,1.84,.70)
                elbow=(.48,1.80,.23)
            self.segment(shoulder,elbow,.17,skin)
            self.segment(elbow,glove,.14,skin)
            self.sphere(glove,.23,color)
        glPopMatrix()

    def hands(self, color, attack=0.0, arm="right", guard=False):
        # Camera-relative first-person arms. Animated forward along -Z.
        for i,s in enumerate((-1,1)):
            is_striking = attack > 0 and ((arm == "left" and s == -1) or (arm == "right" and s == 1))
            extension = (math.sin(min(1.0,attack/.24)*math.pi) * 1.25) if is_striking else 0.0
            x = s * (.43 if guard else .54)
            y = 1.10 if guard else .80
            z = -.84 - extension
            self.segment((s*.67,.18,.20),(x,y-.1,z+.18),.16,(.44,.29,.24))
            self.sphere((x,y,z),.27,color,20)
            self.sphere((x-s*.09,y-.03,z-.11),.11,(.94,.91,.91),14)

    def view(self, player_idx, state, opponent_state, t, solo=False):
        w = self.width if solo else self.width//2
        x = 0 if solo else player_idx*w
        glEnable(GL_SCISSOR_TEST)
        glScissor(x,0,w,self.height)
        glViewport(x,0,w,self.height)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glDisable(GL_SCISSOR_TEST)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(67, w/self.height, .075, 80.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        head_bob = math.sin(t*2.2)*.012
        lean = state.get("lean",0)
        gluLookAt(lean*.15,1.65+head_bob,.60, lean*.20,1.68,-4.0, 0,1,0)
        self.arena()
        opp_color = CORAL if player_idx==0 else CYAN
        my_color = CYAN if player_idx==0 else CORAL
        self.opponent(opp_color, opponent_state["guard"], opponent_state["attack_timer"],
                      opponent_state["hit_flash"], opponent_state.get("lean",0))
        self.hands(my_color, state["attack_timer"],state["attack_arm"],state["guard"])

    def text(self, surf, text, x, y, font=None, color=(245,247,255), center=False):
        im = (font or self.font_small).render(str(text),True,color)
        xx=x-im.get_width()//2 if center else x
        surf.blit(im,(xx,y))

    def overlay(self, players, mode, remaining, sensors, camera=None, finished=None, help_message=None):
        # Use one RGBA texture for 2D UI; the 3D viewport remains depth-tested.
        hud=pygame.Surface((self.width,self.height),pygame.SRCALPHA)
        if mode=="pvp":
            pygame.draw.line(hud,(230,235,240,190),(self.width//2,0),(self.width//2,self.height),3)
        n=1 if mode=="pve" else 2
        for i in range(n):
            sx=(self.width//2)*i if mode=="pvp" else 0
            vw=self.width//2 if mode=="pvp" else self.width
            p=players[i]
            self.text(hud,f"P{i+1}  {p['health']:03d} HP",sx+22,16,self.font_small)
            pygame.draw.rect(hud,(45,50,65,235),(sx+20,54,vw-40,22),border_radius=6)
            fill=max(0,int((vw-40)*p["health"]/100))
            if fill:
                pygame.draw.rect(hud,(42,183,240) if i==0 else (240,76,84),(sx+20,54,fill,22),border_radius=6)
            target=players[1-i]
            self.text(hud,f"OPPONENT {target['health']:03d} HP",sx+22,86,self.font_tiny)
            self.text(hud,"TRACKED" if sensors[i].get("tracked") else "NO POSE",
                      sx+22,112,self.font_tiny,(100,242,145) if sensors[i].get("tracked") else (250,175,100))
            self.text(hud,"GUARD" if p["guard"] else "",sx+vw-135,111,self.font_tiny,(100,242,145))
            self.text(hud,"+",sx+vw//2, self.height//2-17,self.font_big,center=True,color=(255,255,255))
            if p["hit_flash"]>0:
                hit=pygame.Surface((vw,self.height),pygame.SRCALPHA)
                hit.fill((255,30,40,45))
                hud.blit(hit,(sx,0))
        self.text(hud,f"{int(remaining):02d}s  |  {mode.upper()}  |  FPS 3D",
                  self.width//2,12,self.font_small,(255,220,115),center=True)
        if mode=="pve":
            self.text(hud,"BOT",self.width-74,86,self.font_small,(255,120,120))
        if finished:
            dim=pygame.Surface((self.width,self.height),pygame.SRCALPHA)
            dim.fill((0,0,0,190))
            hud.blit(dim,(0,0))
            self.text(hud,finished,self.width//2,self.height//2-40,self.font_big,(255,225,125),center=True)
            self.text(hud,"R: rematch | ESC: quit",self.width//2,self.height//2+20,self.font_small,center=True)
        if help_message:
            self.text(hud,help_message,18,self.height-35,self.font_tiny,(240,240,240))
        if camera is not None:
            # Miniature diagnostic preview, camera pose lines drawn by main module.
            view_w=220
            view_h=round(view_w*camera.get_height()/camera.get_width())
            mini=pygame.transform.smoothscale(camera,(view_w,view_h))
            pygame.draw.rect(hud,(10,15,25,230),(self.width-view_w-12,self.height-view_h-52,view_w+4,view_h+4))
            hud.blit(mini,(self.width-view_w-10,self.height-view_h-50))

        raw=pygame.image.tostring(hud,"RGBA",True)
        glViewport(0,0,self.width,self.height)
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D,self.hud_texture)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,self.width,self.height,0,GL_RGBA,GL_UNSIGNED_BYTE,raw)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0,self.width,0,self.height,-1,1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glColor4f(1,1,1,1)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0);glVertex2f(0,0)
        glTexCoord2f(1,0);glVertex2f(self.width,0)
        glTexCoord2f(1,1);glVertex2f(self.width,self.height)
        glTexCoord2f(0,1);glVertex2f(0,self.height)
        glEnd()
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glEnable(GL_CULL_FACE)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
