from dataclasses import dataclass, field
from enum import Enum
import json

class Color(Enum):
  LEFT = 0
  RIGHT = 1

class Direction(Enum):
  UP = 0
  DOWN = 1
  LEFT = 2
  RIGHT = 3
  UPLEFT = 4
  UPRIGHT = 5
  DOWNLEFT = 6
  DOWNRIGHT = 7
  ANY = 8

@dataclass
class Note:
  beat: float = 0.0
  x: int = 0 # horiz pos 0-3 left is 0
  y: int = 0 # vert pos 0-2 top is 2
  color: Color = Color.LEFT
  dir: Direction = Direction.ANY
  angle_offset: float = 0.0

  name_mappings = {
    'b': 'beat',
    'x': 'x',
    'y': 'y',
    'c': 'color',
    'd': 'dir',
    'a': 'angle_offset'
  }
  
  def __init__(self, json_obj):
    for j in json_obj:
      if j in self.name_mappings:
        setattr(self, self.name_mappings[j], type(getattr(self, self.name_mappings[j]))(json_obj[j]))
    
    
@dataclass
class Bomb:
  beat: float = 0.0
  x: int = 0 
  y: int = 0 

  name_mappings = {
    'b': 'beat',
    'x': 'x',
    'y': 'y',
  }
  
  def __init__(self, json_obj):
    for j in json_obj:
      if j in self.name_mappings:
        setattr(self, self.name_mappings[j], type(getattr(self, self.name_mappings[j]))(json_obj[j]))
  
@dataclass
class Wall: # TODO add parsing for 2.6.0 walls
  beat: float = 0.0
  duration: float = 0.0
  x: int = 0 
  y: int = 0 
  width: int = 0
  height: int = 0

  name_mappings = {
    'b': 'beat',
    'x': 'x',
    'y': 'y',
    'd': 'duration',
    'w': 'width',
    'h': 'height'
  }
  
  def __init__(self, json_obj):
    for j in json_obj:
      if j in self.name_mappings:
        setattr(self, self.name_mappings[j], type(getattr(self, self.name_mappings[j]))(json_obj[j]))

class Difficulty(Enum):
  EASY = 1
  NORMAL = 3
  HARD = 5
  EXPERT = 7
  EXPERTPLUS = 9

class Lightshow: # TODO
  def __init__(self) -> None:
    pass

@dataclass
class BeatMap:
  difficulty: Difficulty = Difficulty.EASY
  beatmap_file: str = "no file"
  njs: float = 20.0
  nj_offset: float = 0.0

  name_mappings = {
    '_difficultyRank': 'difficulty',
    '_beatmapFilename': 'beatmap_file',
    "_noteJumpMovementSpeed": 'njs',
    "_noteJumpStartBeatOffset": 'nj_offset',
  }

  def __init__(self, folder, json_obj, bpm):
    self.folder = folder
    self.bpm = bpm
    for j in json_obj:
      if j in self.name_mappings:
        setattr(self, self.name_mappings[j], type(getattr(self, self.name_mappings[j]))(json_obj[j]))

    with open(f'{folder}/{self.beatmap_file}', 'r') as f:
      data = json.loads(f.read())
    self.notes = [Note(x) for x in data['colorNotes']]
    self.bombs = [Bomb(x) for x in data['bombNotes']]
    self.walls = [Wall(x) for x in data['obstacles']]
    self.hjd = self.calc_hjd()

  def calc_hjd(self):
    hj = 4
    n = 60/self.bpm
    while(self.njs*n*hj > 18): hj /= 2
    
    hj += self.nj_offset
    if(hj < 0.25): hj = 0.25
  
    return hj
  
  def get_hjd(self):
    return self.hjd
  
  def get_njd(self):
    return self.njs * self.get_hjd() * 60 / self.bpm
    

"""hjd calculation
		let halfjump = 4;
		let num = 60 / bpm;

		// Need to repeat this here even tho it's in BeatmapInfo because sometimes we call this function directly
		if (njs <= 0.01)
			// Is it ok to == a 0f?
			njs = 10;

		while (njs * num * halfjump > 18) halfjump /= 2;

		halfjump += offset;
		if (halfjump < 0.25) halfjump = 0.25;

		return halfjump;
"""

@dataclass
class WholeMap:
  folder: str = ""
  version: str = "no version"
  song_name: str = "no song"
  song_subname: str = "no subname"
  song_author: str = "no author"
  song_file: str = "no song file"
  cover_image: str = "no cover image"
  bpm: float = 120.0
  song_length: float = 0.0 # TODO add parsing for song length (not in metadata)
  song_offset: float = 0.0
  swing_shuffle: float = 0.0
  swing_shuffle_period: float = 0.0
  preview_start_time: float = 0.0
  preview_duration: float = 0.0
  beatmaps: list[BeatMap] = field(default_factory=list) #TODO add support for noodlemap????
  # environment not necessary

  name_mappings = {
    '_version': 'version',
    '_songName': 'song_name',
    '_songSubName': 'song_subname',
    '_songAuthorName': 'song_author',
    '_songFilename': 'song_file',
    '_coverImageFilename': 'cover_image',
    '_beatsPerMinute': 'bpm',
    '_songTimeOffset': 'song_offset',
    '_shuffle': 'swing_shuffle',
    '_shufflePeriod': 'swing_shuffle_period',
    '_previewStartTime': 'preview_start_time',
    '_previewDuration': 'preview_duration'
  }

  def __init__(self, folder):
    self.folder = folder
    with open(f'{self.folder}/Info.dat', 'r') as f:
      json_obj = json.loads(f.read())
    for j in json_obj:
      if j in self.name_mappings:
        setattr(self, self.name_mappings[j], json_obj[j])
    self.beatmaps = list()
    self.parse_beatmaps(json_obj['_difficultyBeatmapSets'])
  
  def parse_beatmaps(self, beatmaps_obj):
    for a in [x["_difficultyBeatmaps"] for x in beatmaps_obj if x['_beatmapCharacteristicName'] == 'Standard'][0]:
      self.beatmaps.append(BeatMap(self.folder, a, self.bpm))
    # for [map for characteristic in beatmaps_obj for map in characteristic["_difficultyBeatmaps"]]:
  
  def time_to_beat(self, time):
    return time * self.bpm / 60
  
  def beat_to_time(self, beat):
    return beat * 60 / self.bpm
  