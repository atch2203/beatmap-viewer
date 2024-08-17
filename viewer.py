from collections import deque
from bsor.Bsor import make_bsor
from bsor.Scoring import calc_stats

from map import BeatMap, Direction, Note, Object, Objtype, WholeMap, Color as mapColor
import shutil


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

xy_spacing = 0.5
z_speed = 2


class Obj:
  despawn_buffer: float = 0 # in beats
  assets: list[Entity]
  overall_z: float = 0
  z_offset: float = 0
  end: float #point for despawning in beats

  def __init__(self, obj: Object, spawn_z: float, njs: float, btt):
    self.assets = list()
    self.obj = obj
    application.asset_folder = Path(".")
    match obj.objtype:
      case Objtype.NOTE:
        self.assets.append(Entity(model='model/beat.obj', color=(rgb(1, 0, 0) if obj.color == mapColor.LEFT else rgb(0, 0, 1))))
        if obj.dir == Direction.ANY:
          self.assets.append(Entity(model='model/dot.obj', color=rgb(1, 1, 1)))
        else:
          self.assets.append(Entity(model='model/arrow.obj', color=rgb(1, 1, 1)))
        self.end = obj.beat
      case Objtype.BOMB:
        self.assets.append(Entity(model='model/bomb.obj', color=rgb(0,0,0)))
        self.end = obj.beat
      case Objtype.WALL:
        wall = Entity(model='cube', color=rgb(0,1,0), alpha=0.2, scale=xy_spacing)
        wall.scale_x *= obj.width
        wall.scale_y *= obj.height
        z_thing = btt(obj.duration) * njs * z_speed / xy_spacing
        wall.scale_z *= z_thing
        self.end = obj.beat + obj.duration
        self.z_offset = (z_thing) / 4
        self.assets.append(wall)
    for asset in self.assets:
      asset.rotation_x = 180
      if obj.objtype is Objtype.NOTE:
        asset.rotation_z = dir_to_angle[obj.dir]
      asset.position = (obj.x * xy_spacing, obj.y * xy_spacing, spawn_z + self.z_offset)
    
    self.overall_z = spawn_z + self.z_offset
        
  def move_z(self, dz):
    self.overall_z -= dz
    for a in self.assets:
      a.z = self.overall_z
    
  def set_z(self, z):
    self.overall_z = z + self.z_offset
    for a in self.assets:
      a.z = self.overall_z
  
  def despawn(self):
    for a in self.assets:
      a.disable()
  

class Replay(Entity):
  cur_beat = 0
  spawn_beat = 0
  next_obj_despawn = 0
  next_obj_spawn = 0
  paused = True
  despawn_offset = 0 #in beats, higher means bloq stays longer
  total_time = ''

  def __init__(self, name, diffid):
    self.map: WholeMap = WholeMap(name)
    self.beatmap: BeatMap = self.map.beatmaps[diffid]
    self.obj_entities: deque[Obj] = deque()
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
    for n in self.obj_entities:
      n.set_z(self.map.beat_to_time(n.obj.beat - self.cur_beat)*(self.beatmap.njs)*z_speed)
    self.despawn_objects()
    self.spawn_objects()
    
    self.update_slider()

  def despawn_objects(self):
    while self.obj_entities and self.obj_entities[0].end + self.despawn_offset < self.cur_beat:
      self.obj_entities.popleft().despawn()
  
  def spawn_objects(self):
    while self.next_obj_spawn < len(self.beatmap.objects) and self.spawn_beat > self.beatmap.objects[self.next_obj_spawn].beat:
      spawn_z = self.map.beat_to_time(self.beatmap.objects[self.next_obj_spawn].beat - self.cur_beat)*(self.beatmap.njs)*z_speed

      insert_pos = len(self.obj_entities)
      obj_insert = Obj(self.beatmap.objects[self.next_obj_spawn], spawn_z, self.beatmap.njs, self.map.beat_to_time)
      while insert_pos > 0 and obj_insert.end < self.obj_entities[insert_pos-1].end: insert_pos -= 1
      self.obj_entities.insert(insert_pos, obj_insert)
      self.next_obj_spawn += 1

  def go_to_beat(self, beat: float):
    self.clear_objs()

    self.cur_beat = beat
    self.spawn_beat = self.cur_beat + self.beatmap.get_hjd()

    self.next_obj_despawn = 0 
    while self.next_obj_despawn < len(self.beatmap.objects) and self.cur_beat > self.beatmap.objects[self.next_obj_despawn].beat + self.beatmap.objects[self.next_obj_despawn].duration+ self.despawn_offset:
      self.next_obj_despawn += 1

    self.next_obj_spawn = self.next_obj_despawn
    self.spawn_objects()

    self.audio.stop(destroy=False)
    if not self.paused:
      self.audio.play(start=(self.map.beat_to_time(self.cur_beat)+self.map.song_offset))

  def clear_objs(self):
    while self.obj_entities: self.obj_entities.popleft().despawn()

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

  def next(self, sec):
    self.go_to_beat(min(self.cur_beat + self.map.time_to_beat(sec), self.map.time_to_beat(self.audio.length)-0.01))
    self.update_slider()
  
  def prev(self, sec):
    self.go_to_beat(max(self.cur_beat - self.map.time_to_beat(sec), 0))
    self.update_slider()
  
  def pauseplay(self):
    self.paused = not self.paused
    if self.paused:
      self.audio.stop(destroy=False)
    else:
      self.audio.play(start=(self.map.beat_to_time(self.cur_beat)+self.map.song_offset))
    self.update_slider()

  #endregion 

  #region ======================= AUDIO MANAGEMENT ===================================

  def init_audio(self):
    application.asset_folder = Path(f"{self.map.folder}")
    shutil.copyfile(f'{self.map.folder}/{self.map.song_file}', f'{self.map.folder}/{self.map.song_file.replace('.egg', '.ogg')}')
    self.audio = Audio(sound_file_name=f'{self.map.song_file.replace('.egg', '.ogg')}', autoplay=False)
    self.audio.stop(destroy=False)

  #endregion
      



# replay = Replay("/home/alex/beatsaber/maps/3a7a2 (RATATA - Hener & Harper)", 2)
# replay = Replay("/home/alex/beatsaber/maps/2b868 (mitsukiyo & Lee Jin-ah - Target For Love - staryouh)", 0)
# replay = Replay("/home/alex/beatsaber/maps/31d13 (Luminency - Fnyt)", 2)
replay = Replay("/home/alex/beatsaber/maps/298b5 (Last Wish - BSWC Team)", 4)

def input(key):
  match(key): 
    case 'right arrow': replay.next(5)
    case 'left arrow': replay.prev(5)
    case '.': replay.next(0.1)
    case ',': replay.prev(0.1)
    case 'space': replay.pauseplay()
  
print(replay.map.beat_to_time(100))
  
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