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

bloq_xy_spacing = 0.5

class Bloq:
  def __init__(self, note: Note, spawn_z: float):
    self.note = note
    application.asset_folder = Path(".")
    if note.dir == Direction.ANY:
      self.deco = Entity(model='model/dot.obj', color=rgb(1, 1, 1))
    else:
      self.deco = Entity(model='model/arrow.obj', color=rgb(1, 1, 1))
    self.cube = Entity(model='model/beat.obj', color=(rgb(1, 0, 0) if note.color == mapColor.LEFT else rgb(0, 0, 1)))
    self.deco.rotation_x = self.cube.rotation_x = 180
    self.deco.rotation_z = self.cube.rotation_z = dir_to_angle[note.dir]
    self.deco.position = self.cube.position = (note.x*bloq_xy_spacing, note.y*bloq_xy_spacing, spawn_z)
  
  def despawn(self):
    self.deco.disable()
    self.cube.disable()
  

#TODO make time control bar

class Replay(Entity):
  cur_beat = 0
  spawn_beat = 0
  next_note_despawn = 0
  next_note_spawn = 0
  paused = True
  despawn_offset = 0 #in beats, higher means bloq stays longer
  total_time = ''

  def __init__(self, name, diffid):
    self.map: WholeMap = WholeMap(name)
    self.beatmap: BeatMap = self.map.beatmaps[diffid]
    self.bloq_entities: deque[Bloq] = deque()
    self.init_audio()
    self.time_controller = Entity()
    self.time_controller.update = self.update
    self.slider = Slider(min=0, max=self.audio.length, default=None, height=Text.size, text='', dynamic=False, bar_color=color.black66)
    self.slider.knob.text_entity.disable()
    self.slider.position = (-0.2, -0.45)
    self.slider.on_value_changed = self.slider_seek
    self.total_time = f'{int(self.audio.length//60)}:{int(self.audio.length%60):02d}'
    self.update_slider()
    self.go_to_beat(0)
    
  #region ===================== UPDATE/TIME MANAGEMENT ==================================
  def update(self):
    if self.paused:
      return
    self.cur_beat += self.map.time_to_beat(time.dt)
    self.spawn_beat = self.cur_beat + self.beatmap.get_hjd()
    for n in self.bloq_entities:
      n.cube.z -= time.dt * self.beatmap.njs
      n.deco.z -= time.dt * self.beatmap.njs
    self.despawn_bloqs()
    self.spawn_bloqs()
    
    self.update_slider()

  def despawn_bloqs(self):
    while self.bloq_entities and self.bloq_entities[0].note.beat + self.despawn_offset < self.cur_beat:
      self.bloq_entities.popleft().despawn()
  
  def spawn_bloqs(self):
    while self.next_note_spawn < len(self.beatmap.notes) and self.spawn_beat > self.beatmap.notes[self.next_note_spawn].beat:
      spawn_z = self.beatmap.get_njd() - (self.beatmap.njs * (self.spawn_beat - self.beatmap.notes[self.next_note_spawn].beat))
      self.bloq_entities.append(Bloq(self.beatmap.notes[self.next_note_spawn], spawn_z))
      self.next_note_spawn += 1

  def go_to_beat(self, beat: float):
    self.clear_notes()

    self.cur_beat = beat
    self.spawn_beat = self.cur_beat + self.beatmap.get_hjd()

    self.next_note_despawn = 0
    while self.next_note_despawn < len(self.beatmap.notes) and self.cur_beat > self.beatmap.notes[self.next_note_despawn].beat + self.despawn_offset:
      self.next_note_despawn += 1

    self.next_note_spawn = self.next_note_despawn
    self.spawn_bloqs()

    self.audio.stop(destroy=False)
    self.audio.play(start=(self.map.beat_to_time(self.cur_beat)+self.map.song_offset))

  def clear_notes(self):
    while self.bloq_entities: self.bloq_entities.popleft().despawn()

#endregion

#region ==================== slider/changing time ========================

  def update_slider(self):
    cur_time = self.map.beat_to_time(self.cur_beat)
    self.slider.value = cur_time
    minutes = int(cur_time // 60)
    seconds = int(cur_time % 60)
    self.slider.label.text = f'{'paused ' if self.paused else ''}{minutes}:{seconds:02d} / {self.total_time}'

  def go_to_time(self, time: float):
    self.go_to_beat(min(self.map.time_to_beat(time), self.map.time_to_beat(self.audio.length)-0.01))
  
  def slider_seek(self):
    self.go_to_time(self.slider.value)

  def next_5(self):
    self.go_to_beat(min(self.cur_beat + self.map.time_to_beat(5), self.map.time_to_beat(self.audio.length)-0.01))
    self.update_slider()
  
  def prev_5(self):
    self.go_to_beat(max(self.cur_beat - self.map.time_to_beat(5), 0))
    self.update_slider()
  
  def pauseplay(self):
    self.paused = not self.paused
    if self.paused:
      self.audio.stop(destroy=False)
    else:
      self.audio.play(start=(self.map.beat_to_time(self.cur_beat)+self.map.song_offset))

  #endregion 

  #region ======================= AUDIO MANAGEMENT ===================================

  def init_audio(self):
    application.asset_folder = Path(f"{self.map.folder}")
    self.audio = Audio(sound_file_name=f'{self.map.song_file.replace('.egg', '.ogg')}', autoplay=False)
    self.audio.stop(destroy=False)

  #endregion
      



replay = Replay("/home/alex/beatsaber/maps/3a7a2 (RATATA - Hener & Harper)", 2)

def input(key):
  match(key): 
    case 'right arrow': replay.next_5()
    case 'left arrow': replay.prev_5()
    case 'space': replay.pauseplay()
  
print(camera.position)
camera.position = Vec3(0.75, 0.7, -7)

EditorCamera()

app.run()



# replay_filename = "/home/alex/beatsaber/maps/76561198246352688-Last Wish-Expert-Standard-C86336B3CA84CD03BC3995FADFD7CFDDE2FD00C0-1723756781.bsor"
# other_replay_filename = "/home/alex/beatsaber/maps/76561198246352688-Last Wish-Hard-Standard-C86336B3CA84CD03BC3995FADFD7CFDDE2FD00C0-1723756425.bsor"
# ratata = "/home/alex/beatsaber/maps/76561198246352688-RATATA-ExpertPlus-Standard-8E4B7917C01E5987A5B3FF13FAA3CA8F27D21D34-1722472664.bsor"
# map_filename= "/home/alex/beatsaber/maps/3a7a2 (RATATA - Hener & Harper)/ExpertPlusStandard.dat"

# with open(ratata, 'rb') as f:
#     m = make_bsor(f)
#     stats=calc_stats(m)
#     print(stats)