"""Frame-rate independent game logic for webcam-controlled first-person boxing."""
from __future__ import annotations
import random


def new_player():
    return {"health":100, "guard":False,"lean":0.0,"attack_timer":0.0,
            "attack_arm":"right","hit_flash":0.0,"cooldown":0.0}


class Match:
    def __init__(self,mode="pvp",difficulty="normal"):
        self.mode=mode
        self.difficulty=difficulty
        self.reset()

    def reset(self):
        self.players=[new_player(),new_player()]
        self.seconds=90.0
        self.finished=None
        self.bot_timer=1.1
        self.bot_guard_timer=0.0
        self.stats=[{"hits":0,"punches":0},{"hits":0,"punches":0}]

    def punch(self,i,arm="right",damage=10):
        if self.finished or self.players[i]["cooldown"]>0:
            return False
        me=self.players[i]
        other=self.players[1-i]
        me["cooldown"]=0.34
        me["attack_timer"]=0.24
        me["attack_arm"]=arm
        self.stats[i]["punches"]+=1
        dealt=2 if other["guard"] else damage
        other["health"]=max(0,other["health"]-dealt)
        other["hit_flash"]=0.20
        self.stats[i]["hits"]+=1
        return True

    def update(self,dt,gestures):
        dt=max(0.0,min(0.1,dt))
        if self.finished:
            return
        self.seconds=max(0.0,self.seconds-dt)
        for p in self.players:
            p["attack_timer"]=max(0,p["attack_timer"]-dt)
            p["hit_flash"]=max(0,p["hit_flash"]-dt)
            p["cooldown"]=max(0,p["cooldown"]-dt)
        for i in (0,1):
            if self.mode=="pve" and i==1:
                continue
            g=gestures[i]
            p=self.players[i]
            # If tracking disappears, guard may not remain permanently active.
            p["guard"]=bool(g.get("tracked") and g.get("guard"))
            p["lean"]=float(g.get("lean",0.0))
            if g.get("punch"):
                self.punch(i,g["punch"])
        if self.mode=="pve":
            self.bot_timer-=dt
            self.bot_guard_timer=max(0,self.bot_guard_timer-dt)
            self.players[1]["guard"]=self.bot_guard_timer>0
            if self.bot_timer<=0:
                cfg={"easy":(2.0,3.0,7,.2),
                     "normal":(1.25,2.15,10,.35),
                     "hard":(.8,1.4,13,.48)}[self.difficulty]
                if random.random()<cfg[3]:
                    self.bot_guard_timer=.7
                    self.bot_timer=.65
                else:
                    self.punch(1,random.choice(["left","right"]),cfg[2])
                    self.bot_timer=random.uniform(cfg[0],cfg[1])
        if self.players[0]["health"]<=0 or self.players[1]["health"]<=0 or self.seconds<=0:
            a,b=self.players[0]["health"],self.players[1]["health"]
            self.finished="PLAYER 1 WINS" if a>b else ("PLAYER 2 WINS" if b>a else "DRAW")
