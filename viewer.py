from collections import deque
from bsor.Bsor import make_bsor
from bsor.Scoring import calc_stats
import io
import os

from map import BeatMap, Direction, Note, WholeMap, Color as mapColor


from ursina import *

app = Ursina()

dir_to_angle = {
  Direction.UP: 0,
  Direction.DOWN: 180,
  Direction.LEFT: 90,
  Direction.RIGHT: -90,
  Direction.UPLEFT: 45,
  Direction.UPRIGHT: -45,
  Direction.DOWNLEFT: 135,
  Direction.DOWNRIGHT: -135,
  Direction.ANY: 0,
}

class Bloq:
  def __init__(self, note: Note, spawn_z: float):
    self.note = note
    if note.dir == Direction.ANY:
      self.deco = Entity(model='model/dot.obj', color=rgb(1, 1, 1))
    else:
      self.deco = Entity(model='model/arrow.obj', color=rgb(1, 1, 1))
    self.cube = Entity(model='model/beat.obj', color=(rgb(1, 0, 0) if note.color == mapColor.LEFT else rgb(0, 0, 1)))
    self.deco.rotation_x = self.cube.rotation_x = 180
    self.deco.rotation_z = self.cube.rotation_z = dir_to_angle[note.dir]
    self.deco.position = self.cube.position = (note.x, note.y, spawn_z)
  
  def despawn(self):
    self.deco.disable()
    self.cube.disable()
  
slider = Slider(min=0, max=1, default=None, height=Text.size, text='slider', dynamic=True, radius=Text.size/2, bar_color=color.black66)
slider.position = (-0.2, -0.45)

#TODO make time control bar + Done: seek cleanup capability

class Replay:
  cur_beat = 0
  spawn_beat = 0
  next_note_despawn = 0
  next_note_spawn = 0
  paused = False

  def __init__(self, name, diffid):
    self.map: WholeMap = WholeMap(name)
    self.beatmap: BeatMap = self.map.beatmaps[diffid]
    self.bloq_entities: deque[Bloq] = deque()
    self.time_controller = Entity()
    self.time_controller.update = self.update
    self.go_to_beat(20)
    

  def update(self):
    if self.paused:
      return
    self.cur_beat += self.map.time_to_beat(time.dt)
    self.spawn_beat = self.cur_beat + self.map.time_to_beat(self.beatmap.get_hjd())
    for n in self.bloq_entities:
      n.cube.z -= time.dt * self.beatmap.njs
      n.deco.z -= time.dt * self.beatmap.njs
    self.despawn_bloqs()
    self.spawn_bloqs()
    
  def despawn_bloqs(self):
    while self.bloq_entities and self.bloq_entities[0].note.beat < self.cur_beat:
      self.bloq_entities.popleft().despawn()
  
  def spawn_bloqs(self):
    while self.spawn_beat > self.beatmap.notes[self.next_note_spawn].beat:
      spawn_z = self.beatmap.get_njd() - (self.beatmap.njs * (self.cur_beat - self.beatmap.notes[self.next_note_spawn].beat))
      self.bloq_entities.append(Bloq(self.beatmap.notes[self.next_note_spawn], spawn_z))
      self.next_note_spawn += 1

  def go_to_beat(self, beat: float):
    self.clear_notes()
    self.cur_beat = beat
    self.spawn_beat = self.cur_beat + self.map.time_to_beat(self.beatmap.get_hjd())
    self.next_note_despawn = 0
    while self.cur_beat > self.beatmap.notes[self.next_note_despawn].beat:
      self.next_note_despawn += 1
    self.next_note_spawn = self.next_note_despawn
    self.spawn_bloqs()
    print(f"{self.cur_beat=}\n{self.spawn_beat=}\n{self.next_note_despawn=}\n{self.next_note_spawn=}")
    
  def clear_notes(self):
    self.bloq_entities = deque()
      
  
   

#TODO make functions to calculate note visibility

#TODO make functions to make/clean up note cube entities


# print(a.beatmaps[0].notes[:20])
# print(a.beatmaps[0].difficulty)



replay = Replay("/home/alex/beatsaber/maps/3a7a2 (RATATA - Hener & Harper)", 2)


# b = []
# for n in replay.map.beatmaps[2].notes:
#   b.append(Bloq(n))


EditorCamera()  # add camera controls for orbiting and moving the camera

app.run()



# replay_filename = "/home/alex/beatsaber/maps/76561198246352688-Last Wish-Expert-Standard-C86336B3CA84CD03BC3995FADFD7CFDDE2FD00C0-1723756781.bsor"
# other_replay_filename = "/home/alex/beatsaber/maps/76561198246352688-Last Wish-Hard-Standard-C86336B3CA84CD03BC3995FADFD7CFDDE2FD00C0-1723756425.bsor"
# ratata = "/home/alex/beatsaber/maps/76561198246352688-RATATA-ExpertPlus-Standard-8E4B7917C01E5987A5B3FF13FAA3CA8F27D21D34-1722472664.bsor"
# map_filename= "/home/alex/beatsaber/maps/3a7a2 (RATATA - Hener & Harper)/ExpertPlusStandard.dat"

# with open(ratata, 'rb') as f:
#     m = make_bsor(f)
#     stats=calc_stats(m)
#     print(stats)