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
from .motion import smooth_value
from .robot_rig import retarget_pose, SmoothRobotPose, BONES
from .hands import pose_arm_joints


class SoloScene(Scene):
    def __init__(self):
        super().__init__()
        self.font_label=pygame.font.SysFont("consolas",20,bold=True)
        self.font_info=pygame.font.SysFont("arial",22,bold=True)
        self.font_heading=pygame.font.SysFont("arial",36,bold=True)
        self.font_small=pygame.font.SysFont("arial",16)
        self.head_screen=None
        self.animation_t=0.
        self.camera_head_x=0.0
        self.shadow_view=False
        self.robot_pose=SmoothRobotPose()
        self.camera_roll=0.0
        # Per-hand pose-driven interpolation; independently smooth both fists.
        self.fist_offsets={"left":[0.,0.,0.],"right":[0.,0.,0.]}
        self.arm_pose={
            "left":{"shoulder":[-.50,-.04,0.],"elbow":[-.70,-.30,.05],"wrist":[-.58,-.16,.28]},
            "right":{"shoulder":[.50,-.04,0.],"elbow":[.70,-.30,.05],"wrist":[.58,-.16,.28]},
        }
        self._preview_cache_source=None
        self._preview_cache_size=None
        self._preview_cache_surface=None
        # Cache all static ring geometry in one OpenGL display list. This
        # removes many Python/OpenGL draw calls from each rendering frame.
        self.arena_list=glGenLists(1)
        glNewList(self.arena_list,GL_COMPILE)
        self.arena_solo()
        glEndList()
        # Allocate the HUD texture once; updates avoid re-allocating each frame.
        glBindTexture(GL_TEXTURE_2D,self.hud_texture)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,self.width,self.height,
                     0,GL_RGBA,GL_UNSIGNED_BYTE,None)
        glLightfv(GL_LIGHT0, GL_POSITION, (2.5, 6.0, 2.5, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (1.0, .98, .94, 1.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (.36,.38,.43,1.0))

    def arena_solo(self):
        """A compact televised boxing arena with readable ring geometry."""
        box(0,-.20,-1.3,11.0,.4,13.0,(.055,.075,.12))
        # Dark blue canvas is easier on the eyes than a white featureless floor.
        box(0,.02,-1.3,8.7,.06,10.0,(.19,.27,.39))
        box(0,.055,-1.3,8.25,.008,9.55,(.23,.32,.45))
        # Mat markings: center logo, corner marks and subtle lane lines.
        box(0,.063,-1.2,1.55,.008,1.55,(.15,.22,.34))
        box(0,.069,-1.2,1.28,.006,1.28,(.28,.39,.54))
        for x in (-3.5,-2.4,2.4,3.5):
            box(x,.063,-1.3,.012,.004,9.35,(.31,.40,.53))
        for z in (-5.35,2.75):
            box(0,.063,z,8.15,.004,.012,(.31,.40,.53))
        # Three ropes around the ring; no near-side rope blocks the camera.
        for y,clr in ((.86,(.82,.16,.22)),(1.25,(.91,.93,.97)),(1.64,(.13,.43,.91))):
            for x in (-4.2,4.2):
                self.segment((x,y,3.6),(x,y,-5.7),.026,clr)
            self.segment((-4.2,y,-5.7),(4.2,y,-5.7),.026,clr)
        for x in (-4.2,4.2):
            for z in (-5.7,3.6):
                box(x,1.3,z,.16,2.7,.18,(.10,.16,.27))
                box(x,1.35,z,.19,.62,.22,(.13,.43,.80) if x<0 else (.78,.17,.23))
                self.sphere((x,2.64,z),.12,(.94,.76,.39),14)
        # Stadium walls, illuminated boards and audience tiers.
        box(0,2.65,-8.5,18,5.5,.30,(.035,.052,.09))
        for y in (2.0,2.35,2.70):
            box(0,y,-8.28,15.5,.025,.08,(.12,.19,.30))
        for i,x in enumerate((-6.5,-3.9,-1.3,1.3,3.9,6.5)):
            box(x,3.15,-8.24,1.75,.44,.10,(.08,.19,.31) if i%2==0 else (.12,.12,.22))
            box(x,3.15,-8.17,1.45,.045,.018,(.14,.62,.95) if i%2==0 else (.94,.26,.31))
        for x in (-7,7):
            box(x,2.6,-1.0,.25,5.3,17.0,(.045,.075,.13))
            for y in (1.9,2.5,3.1):
                box(x*.985,y,-1.0,.03,.025,14.0,(.14,.23,.37))
        box(0,5.28,-1.0,18,.25,17,(.035,.05,.09))
        # Overhead light strips.
        for x in (-5.5,-2.8,0,2.8,5.5):
            box(x,4.95,-4.8,1.25,.035,.16,(.72,.84,1.0))


    def ellipsoid(self, center, scale, color, slices=22):
        """Smooth scaled sphere for less blocky anatomical forms."""
        material(color)
        glPushMatrix()
        glTranslatef(*center)
        glScalef(*scale)
        gluSphere(self.quadric,1.0,slices,max(10,int(slices*.65)))
        glPopMatrix()

    def fighter(self,bot):
        """Procedural opponent with articulated limbs and readable boxing states."""
        x,z=bot["x"],bot["z"]
        t=self.animation_t
        bob=math.sin(t*5.2)*.018
        sway=math.sin(t*1.45)*.035
        recoil=min(1.0,bot["hit_timer"]/.28)
        glPushMatrix()
        glTranslatef(x+sway,bob,z)
        glRotatef(math.sin(t*1.35)*2.0-recoil*7.0,0,1,0)
        skin=(.70,.47,.35)
        shorts=(.075,.12,.22)
        jersey=(.82,.12,.20) if bot["hit_timer"]<=0 else (1.0,.72,.25)
        trim=(.94,.91,.82)
        glove=(.78,.035,.09)
        # Legs: articulated thighs, knees, shins and boxing boots.
        for side in (-1.,1.):
            hip=(side*.23,.98,0.)
            knee=(side*.25,.54,.035+math.sin(t*4+side)*.025)
            ankle=(side*.27,.16,.11)
            self.ellipsoid(hip,(.19,.22,.20),shorts,16)
            self.segment(hip,knee,.135,shorts)
            self.sphere(knee,.12,(.18,.23,.32),14)
            self.segment(knee,ankle,.105,skin)
            box(side*.28,.105,.22,.34,.17,.48,(.055,.09,.17))
        self.ellipsoid((0,.99,0),(.43,.22,.27),shorts,18)
        box(0,1.02,.045,.86,.075,.49,trim)
        # Chest, abdomen and shoulder silhouette.
        self.ellipsoid((0,1.49,0),(.49,.57,.29),jersey,24)
        self.ellipsoid((0,1.16,.035),(.38,.28,.25),jersey,18)
        box(0,1.42,.287,.28,.17,.018,trim)
        self.segment((0,1.91,0),(0,2.08,0),.12,skin)
        # Head with hairline, ears, eyes, brows, nose and mouth.
        self.ellipsoid((0,2.36,.015),(.285,.34,.265),skin,24)
        self.ellipsoid((0,2.59,-.015),(.285,.16,.27),(.055,.045,.05),20)
        self.ellipsoid((-.275,2.34,.015),(.055,.09,.07),skin,14)
        self.ellipsoid((.275,2.34,.015),(.055,.09,.07),skin,14)
        for side in (-1.,1.):
            self.ellipsoid((side*.112,2.39,.244),(.040,.048,.024),(.035,.035,.045),12)
            self.ellipsoid((side*.112,2.40,.266),(.014,.018,.009),(.96,.96,.94),10)
            self.ellipsoid((side*.112,2.465,.245),(.052,.018,.025),(.12,.075,.06),10)
        self.ellipsoid((0,2.29,.285),(.055,.075,.045),skin,12)
        self.ellipsoid((0,2.17,.259),(.075,.012,.012),(.20,.07,.07),12)
        # Arms use separate shoulder, elbow, forearm, wrist and glove joints.
        for side,name in ((-1.,"left"),(1.,"right")):
            shoulder=(side*.46,1.77,.015)
            if bot["guard"]:
                elbow=(side*.49,1.54,.19)
                wrist=(side*.31,1.79,.40)
            else:
                elbow=(side*.62,1.47,.12)
                wrist=(side*.49,1.43,.34)
            if bot["punch_timer"]>0 and bot.get("punch_hand","right")==name:
                phase=max(0.,min(1.,(.28-bot["punch_timer"])/.28))
                k=math.sin(phase*math.pi)
                elbow=(side*.47,1.63,.18+k*.12)
                wrist=(side*.30,1.61,.43+k*.82)
            self.sphere(shoulder,.145,skin,16)
            self.segment(shoulder,elbow,.125,skin)
            self.sphere(elbow,.115,skin,14)
            self.segment(elbow,wrist,.105,skin)
            self.sphere(wrist,.09,skin,14)
            fist=(wrist[0],wrist[1],wrist[2]+.13)
            self.ellipsoid(fist,(.17,.18,.19),glove,20)
            box(fist[0],fist[1]-.12,fist[2]-.005,.22,.065,.16,trim)
        glPopMatrix()


    def player_arms(self, player, control, dt):
        """Render compact camera-space arms; all three joints track separately."""
        p=player
        eye=(p["x"]+self.camera_head_x,1.72,p["z"]+.38)
        measured=pose_arm_joints(control.get("landmarks"),control.get("vis")) if control.get("tracked") else {}
        for side,name in ((-1.,"left"),(1.,"right")):
            fallback={
                "shoulder":(side*.44,-.02,0.),
                "elbow":(side*.62,-.27,.015),
                "wrist":(side*.49,-.20,.035),
            }
            arm=measured.get(name,{})
            for joint in ("shoulder","elbow","wrist"):
                target=arm.get(joint,fallback[joint])
                current=self.arm_pose[name][joint]
                tau=.060 if joint in arm else .19
                for i in range(3):
                    current[i]=smooth_value(current[i],target[i],dt,tau)
            shoulder=self.arm_pose[name]["shoulder"]
            elbow=self.arm_pose[name]["elbow"]
            wrist=self.arm_pose[name]["wrist"]

            # Keep the rig about one metre in front of the eye. The previous
            # 0.38m placement put 26cm gloves almost on the near clipping plane,
            # making them fill the screen and hiding their articulation.
            def world(v,extra_reach=0.):
                return (
                    eye[0]+v[0]*.70,
                    eye[1]-.30+v[1]*.66,
                    eye[2]-1.08+v[2]+extra_reach,
                )
            a=world(shoulder)
            b=world(elbow)
            c=world(wrist)
            wrist_visible=("wrist" in arm and "elbow" in arm)
            if p["punch_timer"]>0 and p["punch_hand"]==name and not wrist_visible:
                phase=max(0.,min(1.,(.27-p["punch_timer"])/.27))
                c=world(wrist,math.sin(phase*math.pi)*.34)

            upper=(.12,.23,.36)
            forearm=(.24,.39,.54)
            joint_color=(.48,.65,.78)
            glove_color=(.035,.39,.76)
            # Upper arm, elbow hinge and forearm are distinct moving links.
            self.ellipsoid(a,(.105,.115,.105),upper,16)
            self.segment(a,b,.078,upper)
            self.ellipsoid(b,(.092,.092,.092),joint_color,16)
            self.segment(b,c,.067,forearm)
            wrist_center=world(wrist,.055)
            glove_center=world(wrist,.155)
            self.segment(c,wrist_center,.060,forearm)
            self.ellipsoid(wrist_center,(.066,.070,.066),joint_color,14)
            self.ellipsoid(glove_center,(.125,.137,.145),glove_color,20)
            # Raised knuckle plate and wrist cuff give the fist readable shape.
            self.ellipsoid((glove_center[0],glove_center[1]+.035,glove_center[2]+.105),
                           (.085,.055,.035),(.12,.53,.88),14)
            strap=(.98,.75,.16) if name=="right" else (.76,.87,.96)
            box(glove_center[0],glove_center[1]-.105,glove_center[2]-.005,
                .19,.055,.15,strap)


    def draw_shadow_robot(self, player, control, dt):
        """Render an original robot with independently articulated limbs."""
        targets=retarget_pose(control.get("landmarks"),control.get("vis"))
        joints=self.robot_pose.update(targets,dt)
        armor=(.15,.50,.73)
        light=(.43,.81,.94)
        gunmetal=(.11,.16,.24)
        steel=(.53,.62,.70)
        glPushMatrix()
        glTranslatef(player["x"],0,player["z"])
        # Dynamic bones from ankles to head; no hardcoded boxing arm pose.
        for left,right in BONES:
            a,b=joints[left],joints[right]
            upper=left.endswith("shoulder") or left.endswith("hip")
            thickness=.13 if upper else .095
            color=gunmetal if ("hip" in left or "knee" in left) else steel
            self.segment(a,b,thickness,color)
        for name,point in joints.items():
            size=.16 if "shoulder" in name or "hip" in name else .11
            if name in ("left_wrist","right_wrist"):
                size=.22
            if name=="head":
                size=.28
            color=armor if name in ("left_wrist","right_wrist","head") else light
            self.sphere(point,size,color,16)
        # Chest follows the actual shoulder/hip positions: draw a bright
        # central power core and joint plates.
        neck=joints["neck"]
        hip=joints["hip_center"]
        core=tuple(hip[i]*.39+neck[i]*.61 for i in range(3))
        self.sphere(core,.19,(.22,.86,.97),18)
        for hand in ("left_wrist","right_wrist"):
            self.sphere(joints[hand],.235,armor,18)
        glPopMatrix()

    def render(self, fight, dt, control=None):
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
        # Actual 3D viewpoint is linked to relative head position and tilt.
        # Render-time easing hides 20-30Hz pose sampling between display frames.
        control=control or {}
        head_target=control.get("head_offset", 0.0) if control.get("tracked") else 0.0
        roll_target=control.get("head_roll", 0.0) if control.get("tracked") else 0.0
        self.camera_head_x=smooth_value(self.camera_head_x,head_target,dt,.105)
        self.camera_roll=smooth_value(self.camera_roll,roll_target,dt,.110)
        angle=math.radians(self.camera_roll)
        # Roll rotates the horizon around the optical axis, while lateral
        # camera displacement produces real parallax in the ring.
        if self.shadow_view:
            # Third-person shadow training shows the player's complete robot
            # and bot simultaneously, essential to calibrate knee/arm/hip.
            eye=(p["x"]+3.6,3.15,p["z"]+5.7)
            target=(p["x"]*.75+fight.bot["x"]*.25,1.42,p["z"]-1.25)
            gluLookAt(*eye,*target,0,1,0)
        else:
            eye=(p["x"]+self.camera_head_x,1.72,p["z"]+.38)
            target=(p["x"]+self.camera_head_x*.30,1.54,p["z"]-5.)
            gluLookAt(*eye,*target,math.sin(angle),math.cos(angle),0)
        glCallList(self.arena_list)
        self.fighter(fight.bot)
        if self.shadow_view:
            self.draw_shadow_robot(p,control,dt)
        # Project bot's actual 3D head into the 2D HUD for the label.
        xx,yy,_=gluProject(fight.bot["x"],2.88,fight.bot["z"],
                            glGetDoublev(GL_MODELVIEW_MATRIX),
                            glGetDoublev(GL_PROJECTION_MATRIX),
                            glGetIntegerv(GL_VIEWPORT))
        self.head_screen=(float(xx),float(self.height-yy))
        if not self.shadow_view:
            self.player_arms(p,control,dt)

    def _hud_text(self,s,text,x,y,font,color=(245,246,248),center=False):
        image=font.render(text,True,color)
        if center:x-=image.get_width()/2
        s.blit(image,(int(x),int(y)))

    def draw_hud(self,fight,control,preview,mode="pose",fps=0,preview_large=True):
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
        self._hud_text(h,"SHADOW ROBOT DEBUG VIEW" if self.shadow_view else "FIRST PERSON BOXING",
                       self.width/2,62,self.font_small,(170,207,250),True)
        self._hud_text(h,f"HEAD {self.camera_roll:+.0f} deg  |  L/ R GLOVE TRACKING",self.width/2,84,self.font_small,(154,236,188),True)
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
        status=("POSE TRACKED" if control.get("tracked") else "NO POSE")
        if not control.get("calibrated",True) and mode != "KEYBOARD DEMO":
            status=f"CALIBRATING {control.get('calibration',0)}% - HOLD STILL"
        self._hud_text(h,status+
                        f"  |  {mode.upper()}  |  DODGE {self.camera_head_x:+.2f}",30,self.height-51,self.font_small,
                        (105,242,153) if control.get("tracked") else (250,180,94))
        if fight.message_timer>0:
            self._hud_text(h,fight.message,self.width/2,125,self.font_heading,(255,208,112),True)
        if fight.finished:
            pygame.draw.rect(h,(6,8,13,210),(0,200,self.width,235))
            self._hud_text(h,fight.finished,self.width/2,245,self.font_heading,(255,210,113),True)
            self._hud_text(h,"R = RESTART   |   ESC = EXIT",self.width/2,307,self.font_info,center=True)
        # Diagnostic camera is deliberately large enough to see the full
        # 33-point skeleton, unlike the old 240x135 preview.
        if preview is not None:
            pw,ph=(365,205) if preview_large else (240,135)
            if preview is not self._preview_cache_source or self._preview_cache_size!=(pw,ph):
                self._preview_cache_surface=pygame.transform.smoothscale(preview,(pw,ph))
                self._preview_cache_source=preview
                self._preview_cache_size=(pw,ph)
            image=self._preview_cache_surface
            x=self.width-pw-20
            y=self.height-ph-45
            pygame.draw.rect(h,(8,12,20,230),(x-4,y-4,pw+8,ph+8),border_radius=7)
            h.blit(image,(x,y))
            self._hud_text(h,"33 POINTS | TAB: ROBOT VIEW | V: SIZE | C: CALIBRATE",x+3,y+ph+7,self.font_small)
        # Transparent HUD, rendered through a single OpenGL texture.
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D,self.hud_texture)
        glTexSubImage2D(GL_TEXTURE_2D,0,0,0,self.width,self.height,
                        GL_RGBA,GL_UNSIGNED_BYTE,pygame.image.tostring(h,"RGBA",True))
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

    def close(self):
        if getattr(self,"arena_list",0):
            glDeleteLists(self.arena_list,1)
            self.arena_list=0
        super().close()
