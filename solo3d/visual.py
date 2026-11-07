"""Improved solo first-person visuals with world-space head coordinates and clean HUD.

Reuses OpenGL primitives from the first 3D prototype while replacing its
UI and fighter construction. This is a stylized 3D game, not a photo renderer.
"""
from __future__ import annotations
import math
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from fps3d.renderer import Scene, box


class SoloScene(Scene):
    def __init__(self):
        super().__init__()
        self.font_label=pygame.font.SysFont("consolas",20,bold=True)
        self.font_info=pygame.font.SysFont("arial",22,bold=True)
        self.font_heading=pygame.font.SysFont("arial",36,bold=True)
        self.font_small=pygame.font.SysFont("arial",16)
        self.head_screen=None
        self.animation_t=0.
        glLightfv(GL_LIGHT0, GL_POSITION, (2.5, 6.0, 2.5, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, .98, .94, 1.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (.36,.38,.43,1.0))

    def arena_solo(self):
        # Warm boxing hall background, roof beams and raised canvas
        box(0,-.20,-1.3,11.0,.4,13.0,(.13,.18,.24))
        box(0,.02,-1.3,8.7,.06,10.0,(.64,.70,.78))
        # square floor grid with light blue lines
        for i in range(-4,5):
            box(i,.058,-1.3,.018,.006,9.80,(.50,.57,.65))
        for i in range(-6,4):
            box(0,.058,i,8.45,.006,.018,(.50,.57,.65))
        box(0,.066,-1.1,2.0,.008,2.0,(.29,.36,.50))
        # Only side and back ropes (front ropes would block first-person view).
        for y,clr in ((.86,(.79,.15,.19)),(1.25,(.94,.94,.97)),(1.64,(.13,.38,.83))):
            for x in (-4.2,4.2):
                self.segment((x,y,3.6),(x,y,-5.7),.024,clr)
            self.segment((-4.2,y,-5.7),(4.2,y,-5.7),.024,clr)
        for x in (-4.2,4.2):
            for z in (-5.7,3.6):
                box(x,1.3,z,.14,2.7,.14,(.15,.20,.30))
                self.sphere((x,2.64,z),.11,(.92,.74,.35),12)
        # Stadium wall, strips and light panels
        box(0,2.7,-8.5,18,5.7,.28,(.055,.082,.13))
        for x in (-6,-3,0,3,6):
            box(x,4.50,-8.30,1.1,.08,.16,(.36,.54,.84))
        for x in (-7,7):
            box(x,2.6,-1.0,.25,5.3,17.0,(.07,.11,.18))
        box(0,5.28,-1.0,18,.25,17,(.06,.08,.14))

    def fighter(self,bot):
        x,z=bot["x"],bot["z"]
        glPushMatrix()
        glTranslatef(x,0,z)
        # Small side-to-side motion, model faces camera (+Z).
        glRotatef(math.sin(self.animation_t*1.9)*3,0,1,0)
        skin=(.75,.51,.38)
        jersey=(.89,.19,.23) if bot["hit_timer"]<=0 else (.99,.83,.40)
        dark=(.13,.18,.28)
        accent=(.97,.86,.68)
        # Feet and legs (cylinders)
        for side in (-1.,1.):
            px=side*.22
            self.segment((px,.90,0),(px*1.1,.52,.02),.15,dark)
            self.segment((px*1.1,.52,.02),(px*1.15,.13,.13),.14,skin)
            box(px*1.2,.11,.25,.32,.19,.58,dark)
        box(0,.99,0,.92,.38,.58,dark)
        box(0,1.12,.14,.85,.12,.62,accent)
        box(0,1.54,0,.96,.90,.53,jersey)
        box(0,1.75,.285,.37,.18,.016,accent)
        self.segment((0,1.99,0),(0,2.11,0),.17,skin)
        self.sphere((0,2.36,.045),.32,skin,24)
        # Hair, nose and eyes on the face pointed toward +Z.
        self.sphere((0,2.60,-.015),.255,(.10,.075,.067),20)
        for side in (-1.,1.):
            self.sphere((side*.12,2.39,.31),.041,(.06,.06,.09),12)
            self.sphere((side*.12,2.40,.335),.012,(.95,.95,.96),10)
        self.sphere((0,2.29,.35),.078,skin,12)
        box(0,2.15,.29,.17,.018,.023,(.23,.09,.09))
        # Gloves with wrist straps and visible punch animation
        for side in (-1.,1.):
            shoulder=(side*.52,1.83,0)
            elbow=(side*.70,1.60,.20)
            glove=(side*.34,2.08,.60) if bot["guard"] else (side*.66,1.86,.72)
            if bot["punch_timer"]>0 and side==1:
                k=math.sin((.28-bot["punch_timer"])/.28*math.pi)
                elbow=(side*.52,1.84,.20+k*.33)
                glove=(side*.28,1.90,.65+k*.98)
            self.segment(shoulder,elbow,.17,skin)
            self.segment(elbow,glove,.15,skin)
            self.sphere(glove,.24,jersey,20)
            box(glove[0],glove[1]-.15,glove[2]-.01,.31,.10,.27,accent)
        glPopMatrix()

    def player_gloves(self, player):
        # Visible first-person gloves follow the moving camera.
        x,z=player["x"],player["z"]
        for side in (-1.,1.):
            active=player["punch_timer"]>0 and (
                (player["punch_hand"]=="left" and side<0) or
                (player["punch_hand"]=="right" and side>0)
            )
            phase=max(0.,min(1.,(.27-player["punch_timer"])/.27))
            extension=math.sin(phase*math.pi)*1.1 if active else 0.
            gx=x+side*(.50 if player["guard"] else .73)
            gy=1.40 if player["guard"] else 1.05
            gz=z-.52-extension
            forearm=(x+side*.92,.60,z+.08)
            self.segment(forearm,(gx,gy-.09,gz+.14),.19,(.58,.36,.27))
            self.sphere((gx,gy,gz),.31,(.05,.47,.92),24)
            box(gx,gy-.22,gz+.04,.33,.13,.30,(.94,.94,.95))

    def render(self, fight, dt):
        self.animation_t+=dt
        glViewport(0,0,self.width,self.height)
        glClearColor(.038,.052,.079,1)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(74,self.width/self.height,.07,70)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        p=fight.player
        # Camera remains first-person; movement is in real 3D world coordinates.
        eye=(p["x"],1.72,p["z"]+.38)
        target=(p["x"],1.54,p["z"]-5.)
        gluLookAt(*eye,*target,0,1,0)
        self.arena_solo()
        self.fighter(fight.bot)
        # Project bot's actual 3D head into the 2D HUD for the label.
        xx,yy,_=gluProject(fight.bot["x"],2.88,fight.bot["z"],
                            glGetDoublev(GL_MODELVIEW_MATRIX),
                            glGetDoublev(GL_PROJECTION_MATRIX),
                            glGetIntegerv(GL_VIEWPORT))
        self.head_screen=(float(xx),float(self.height-yy))
        self.player_gloves(p)

    def _hud_text(self,s,text,x,y,font,color=(245,246,248),center=False):
        image=font.render(text,True,color)
        if center:x-=image.get_width()/2
        s.blit(image,(int(x),int(y)))

    def draw_hud(self,fight,control,preview,mode="pose",fps=0):
        h=pygame.Surface((self.width,self.height),pygame.SRCALPHA)
        # Opaque upper strip keeps text readable and never overlaps with HP.
        pygame.draw.rect(h,(9,17,29,223),(0,0,self.width,106))
        self._hud_text(h,f"YOU  {fight.player['hp']:03d} HP",32,14,self.font_info)
        self._hud_text(h,f"BOT  {fight.bot['hp']:03d} HP",self.width-268,14,self.font_info)
        pygame.draw.rect(h,(38,48,64),(32,49,365,23),border_radius=5)
        pygame.draw.rect(h,(38,48,64),(self.width-397,49,365,23),border_radius=5)
        if fight.player["hp"]>0:
            pygame.draw.rect(h,(34,170,243),(32,49,round(365*fight.player["hp"]/100),23),border_radius=5)
        if fight.bot["hp"]>0:
            pygame.draw.rect(h,(234,62,78),(self.width-397,49,round(365*fight.bot["hp"]/100),23),border_radius=5)
        self._hud_text(h,f"{int(fight.seconds):02d}s",self.width/2,10,self.font_heading,(255,215,110),True)
        self._hud_text(h,"SOLO BOXING 3D",self.width/2,62,self.font_small,(170,207,250),True)
        # Real projected coordinates above the bot's head.
        if self.head_screen is not None:
            x,y=self.head_screen
            if 0<x<self.width and 115<y<self.height-80:
                label=f"BOT  X:{fight.bot['x']:+.1f}  Z:{fight.bot['z']:+.1f}"
                txt=self.font_label.render(label,True,(252,243,190))
                rect=pygame.Rect(int(x-txt.get_width()/2-10),int(y-3),txt.get_width()+20,txt.get_height()+8)
                pygame.draw.rect(h,(8,14,22,205),rect,border_radius=7)
                h.blit(txt,(rect.x+10,rect.y+3))
        # Fixed status panel.
        pygame.draw.rect(h,(9,17,29,207),(15,self.height-112,465,98),border_radius=12)
        self._hud_text(h,f"YOU  X:{fight.player['x']:+.2f}   Z:{fight.player['z']:+.2f}",30,self.height-103,self.font_info,(105,217,255))
        self._hud_text(h,f"DISTANCE {fight.distance():.2f} m (virtual)  |  FPS {fps:.0f}",30,self.height-74,self.font_small)
        self._hud_text(h,("POSE TRACKED" if control.get("tracked") else "NO POSE")+
                        f"  |  {mode.upper()}",30,self.height-51,self.font_small,
                        (105,242,153) if control.get("tracked") else (250,180,94))
        if fight.message_timer>0:
            self._hud_text(h,fight.message,self.width/2,125,self.font_heading,(255,208,112),True)
        if fight.finished:
            pygame.draw.rect(h,(6,8,13,210),(0,200,self.width,235))
            self._hud_text(h,fight.finished,self.width/2,245,self.font_heading,(255,210,113),True)
            self._hud_text(h,"R = RESTART   |   ESC = EXIT",self.width/2,307,self.font_info,center=True)
        # Picture-in-picture camera pose diagnostics at bottom right.
        if preview is not None:
            pw,ph=240,135
            image=pygame.transform.smoothscale(preview,(pw,ph))
            x=self.width-pw-20
            y=self.height-ph-45
            pygame.draw.rect(h,(8,12,20,230),(x-4,y-4,pw+8,ph+8),border_radius=7)
            h.blit(image,(x,y))
            self._hud_text(h,"CAMERA + POSE",x+3,y+ph+7,self.font_small)
        # Transparent HUD, rendered through a single OpenGL texture.
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D,self.hud_texture)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,self.width,self.height,0,GL_RGBA,GL_UNSIGNED_BYTE,
                     pygame.image.tostring(h,"RGBA",True))
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
