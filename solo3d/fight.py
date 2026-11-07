"""Single-player boxing mechanics: 3D positions, reach-based hits, bot pursuit."""
from __future__ import annotations
import math
import random


def clamp(x, a, b):
    return max(a,min(b,x))


class Fight:
    def __init__(self,difficulty="normal"):
        self.difficulty=difficulty
        self.reset()

    def reset(self):
        self.player={"x":0.,"z":2.95,"hp":100,"guard":False,"punch_timer":0.,"punch_hand":"right","hit_timer":0.}
        self.bot={"x":0.,"z":-1.65,"hp":100,"guard":False,"punch_timer":0.,"punch_hand":"right","hit_timer":0.}
        self.seconds=90.
        self.finished=None
        self.player_cd=0.
        self.bot_cd=0.
        self.hits=0
        self.misses=0
        self.bot_phase=0.
        self.bot_guard_timer=0.
        self.message=""
        self.message_timer=0.
        self.dodges=0
        self.dodge_cooldown=0.0

    def distance(self):
        p,b=self.player,self.bot
        return math.hypot(p["x"]-b["x"],p["z"]-b["z"])

    def _message(self,text):
        self.message=text
        self.message_timer=.65

    def user_attack(self,hand="right"):
        if self.finished or self.player_cd>0: return False
        self.player_cd=.37
        self.player["punch_timer"] = .27
        self.player["punch_hand"]=hand
        # Reach is measured in virtual world space. No more remote damage.
        if self.distance()>2.35:
            self.misses+=1
            self._message("OUT OF RANGE - STEP FORWARD")
            return False
        damage=3 if self.bot["guard"] else 10
        self.bot["hp"]=max(0,self.bot["hp"]-damage)
        self.bot["hit_timer"]=.20
        self.hits+=1
        self._message("BLOCK!" if self.bot["guard"] else f"HIT -{damage}")
        return True

    def update(self,dt,control,move=(0.,0.),force_punch=None):
        dt=clamp(dt,0.,.08)
        if self.finished:return
        self.seconds=max(0.,self.seconds-dt)
        self.message_timer=max(0.,self.message_timer-dt)
        self.player_cd=max(0.,self.player_cd-dt)
        self.bot_cd=max(0.,self.bot_cd-dt)
        self.dodge_cooldown=max(0.,self.dodge_cooldown-dt)
        self.bot_guard_timer=max(0.,self.bot_guard_timer-dt)
        for p in (self.player,self.bot):
            p["punch_timer"]=max(0.,p["punch_timer"]-dt)
            p["hit_timer"]=max(0.,p["hit_timer"]-dt)

        p,b=self.player,self.bot
        if control.get("tracked"):
            target_x=control["x"]
            target_z=control["z"]
            alpha=min(1.,dt*8.)
            p["x"] += (target_x-p["x"])*alpha
            p["z"] += (target_z-p["z"])*alpha
            p["guard"]=bool(control.get("guard"))
        else:
            p["guard"]=False

        # Optional keyboard for small corrections and graphics-only testing.
        dx,dz=move
        p["x"]=clamp(p["x"]+dx*dt*2.3,-2.8,2.8)
        p["z"]=clamp(p["z"]+dz*dt*2.3,.4,3.8)
        self.bot_phase+=dt
        distance=self.distance()
        settings={"easy":(.85,1.8,2.2,5), "normal":(1.15,1.1,1.45,8),
                  "hard":(1.42,.72,1.0,11)}[self.difficulty]
        speed,attack_rate,desired_range,base_damage=settings

        # Chase, retreat, side-step. Bot is a world-space character,
        # not a figure glued to the player's view.
        dx_to=p["x"]-b["x"]
        dz_to=p["z"]-b["z"]
        factor=dt*speed
        if distance>desired_range+.3:
            b["x"]+=clamp(dx_to,-1.,1.)*factor*.72
            b["z"]+=clamp(dz_to,-1.,1.)*factor
        elif distance<desired_range-.3:
            b["z"]-=factor*.75
        b["x"]+=math.sin(self.bot_phase*1.3)*dt*.37
        b["x"]=clamp(b["x"],-2.7,2.7)
        b["z"]=clamp(b["z"],-3.8,.45)

        # Bot blocks with a timed, visible gesture.
        b["guard"]=self.bot_guard_timer>0
        if self.bot_cd<=0 and self.distance()<2.2:
            if random.random()<.28:
                self.bot_guard_timer=.65
                self.bot_cd=.85
            else:
                b["punch_timer"] = .28
                b["punch_hand"]=random.choice(["left","right"])
                if self.distance()<1.95:
                    # A dodge must exceed a real head-lean threshold.
                    # It affects hit testing, not just the rendered camera.
                    lean=abs(float(control.get("head_offset",0.0)))
                    roll=abs(float(control.get("head_roll",0.0)))
                    dodging=bool(control.get("tracked") and
                                 (lean>.23 or roll>14.0))
                    if dodging and self.dodge_cooldown<=0.0:
                        self.dodges+=1
                        self.dodge_cooldown=.52
                        self._message("DODGE!")
                    else:
                        damage=2 if p["guard"] else base_damage
                        p["hp"]=max(0,p["hp"]-damage)
                        p["hit_timer"]=.28
                        self._message("YOU BLOCKED!" if p["guard"] else f"BOT HIT -{damage}")
                self.bot_cd=attack_rate+random.random()*.3
        hand=force_punch or control.get("punch")
        if hand:self.user_attack(hand)
        if p["hp"]<=0:self.finished="YOU LOST"
        elif b["hp"]<=0:self.finished="YOU WIN"
        elif self.seconds<=0:
            self.finished="YOU WIN" if p["hp"]>b["hp"] else ("YOU LOST" if p["hp"]<b["hp"] else "DRAW")
