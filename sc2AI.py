import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
import random
import cv2
import numpy as np
from pprint import pprint

class ExifienceBot(sc2.BotAI):
 def __init__(self):
  self.ITERATIONS_PER_MINUTE = 165
  self.MAX_WORKERS = 50

 async def on_step(self, iteration):
  self.iteration = iteration
  await self.distribute_workers()
  await self.build_workers()
  await self.build_pylons()
  await self.build_assimilators()
  await self.expand()
  await self.offensive_force_buildings()
  await self.build_offensive_force()
  await self.intel()
  await self.defend()
  await self.scout()
  '''
 def random_location_variance(self, enemy_start_location):
  x = enemy_start_location[0]
  y = enemy_start_location[1]

  x += ((random.randrange(-20, 20))/100) * enemy_start_location[0]
  y += ((random.randrange(-20, 20))/100) * enemy_start_location[1]
  
  if x < 0:
   x = 0
  if y < 0:
   y = 0
  if x > self.game_info.map_size[0]:
   x = self.game_info.map_size[0]
  if y > self.game_info.map_size[1]:
   y = self.game_info.map_size[1]
  
  #go_to = position.Point2(position.Pointlike((x,y)))
  return x
  '''
 async def scout(self):
  if len(self.units(OBSERVER)) > 0:
   scout = self.units(OBSERVER)[0]
   if scout.is_idle:
    enemy_location = self.enemy_start_locations[0]
    #move_to = self.random_location_variance(enemy_location)
    #print(move_to)
    await self.do(scout.move(enemy_location))

  else:
   for rf in self.units(ROBOTICSFACILITY).ready.noqueue:
    if self.can_afford(OBSERVER) and self.supply_left > 0:
     await self.do(rf.train(OBSERVER))

 async def intel(self):
  # for game_info: https://github.com/Dentosal/python-sc2/blob/master/sc2/game_info.py#L162
  #print(self.game_info.map_size)
  # flip around. It's y, x when you're dealing with an array.
  game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

  # UNIT: [SIZE, (BGR COLOR)]
  '''from sc2.constants import NEXUS, PROBE, PYLON, ASSIMILATOR, GATEWAY, \
 CYBERNETICSCORE, STARGATE, VOIDRAY'''
  draw_dict = {
      NEXUS: [15, (0, 255, 0)],
      PYLON: [3, (20, 235, 0)],
      PROBE: [1, (55, 200, 0)],
      ASSIMILATOR: [2, (55, 200, 0)],
      GATEWAY: [3, (200, 100, 0)],
      CYBERNETICSCORE: [3, (150, 150, 0)],
      STARGATE: [5, (255, 0, 0)],
      ROBOTICSFACILITY: [5, (215, 155, 0)],

      VOIDRAY: [3, (255, 100, 0)],
      #OBSERVER: [3, (255, 255, 255)],
     }

  for unit_type in draw_dict:
   for unit in self.units(unit_type).ready:
    pos = unit.position
    cv2.circle(game_data, (int(pos[0]), int(pos[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1)



  main_base_names = ["nexus", "supplydepot", "hatchery"]
  for enemy_building in self.known_enemy_structures:
   pos = enemy_building.position
   if enemy_building.name.lower() not in main_base_names:
    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 5, (200, 50, 212), -1)
  for enemy_building in self.known_enemy_structures:
   pos = enemy_building.position
   if enemy_building.name.lower() in main_base_names:
    cv2.circle(game_data, (int(pos[0]), int(pos[1])), 15, (0, 0, 255), -1)

  for enemy_unit in self.known_enemy_units:

   if not enemy_unit.is_structure:
    worker_names = ["probe",
            "scv",
            "drone"]
    # if that unit is a PROBE, SCV, or DRONE... it's a worker
    pos = enemy_unit.position
    if enemy_unit.name.lower() in worker_names:
     cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (55, 0, 155), -1)
    else:
     cv2.circle(game_data, (int(pos[0]), int(pos[1])), 3, (50, 0, 215), -1)

  for obs in self.units(OBSERVER).ready:
   pos = obs.position
   cv2.circle(game_data, (int(pos[0]), int(pos[1])), 1, (255, 255, 255), -1)

  # flip horizontally to make our final fix in visual representation:
  flipped = cv2.flip(game_data, 0)
  resized = cv2.resize(flipped, dsize=None, fx=2, fy=2)

  cv2.imshow('Intel', resized)
  cv2.waitKey(1)

 async def build_workers(self):
  if (len(self.units(NEXUS)) * 16) > len(self.units(PROBE)) and len(self.units(PROBE)) < self.MAX_WORKERS:
   for nexus in self.units(NEXUS).ready.noqueue:
    if self.can_afford(PROBE):
     await self.do(nexus.train(PROBE))


 async def build_pylons(self):
  if self.supply_left < 5 and not self.already_pending(PYLON):
   nexuses = self.units(NEXUS).ready
   if nexuses.exists:
    nexus = nexuses.first
    if self.can_afford(PYLON):
     await self.build(PYLON, near=nexus.position.towards(self.game_info.map_center, 5))

 async def build_assimilators(self):
  for nexus in self.units(NEXUS).ready:
   vaspenes = self.state.vespene_geyser.closer_than(15.0, nexus)
   for vaspene in vaspenes:
    if not self.can_afford(ASSIMILATOR):
     break
    worker = self.select_build_worker(vaspene.position)
    if worker is None:
     break
    if not self.units(ASSIMILATOR).closer_than(1.0, vaspene).exists:
     await self.do(worker.build(ASSIMILATOR, vaspene))

 async def expand(self):
  if self.units(NEXUS).amount < (self.iteration / self.ITERATIONS_PER_MINUTE) and self.can_afford(NEXUS):
   await self.expand_now()

 async def offensive_force_buildings(self):
  #print(self.iteration / self.ITERATIONS_PER_MINUTE)
  if self.units(PYLON).ready.exists:
   pylon = self.units(PYLON).ready.random

   if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE):
    if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
     await self.build(CYBERNETICSCORE, near=pylon.position.towards(self.game_info.map_center, 5))

   elif len(self.units(GATEWAY)) < 1:
    if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
     await self.build(GATEWAY, near=pylon.position.towards(self.game_info.map_center, 5))

   if self.units(CYBERNETICSCORE).ready.exists:
    if len(self.units(ROBOTICSFACILITY)) < 1:
     if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
      await self.build(ROBOTICSFACILITY, near=pylon)

   if self.units(CYBERNETICSCORE).ready.exists:
    if len(self.units(STARGATE)) < ((self.iteration / self.ITERATIONS_PER_MINUTE)/2):
     if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
      await self.build(STARGATE, near=pylon.position.towards(self.game_info.map_center, 5))

 async def build_offensive_force(self):
  for sg in self.units(STARGATE).ready.noqueue:
   if self.can_afford(VOIDRAY) and self.supply_left > 0:
    await self.do(sg.train(VOIDRAY))

 def find_target(self, state):
  if len(self.known_enemy_units) > 0:
   return random.choice(self.known_enemy_units)
  elif len(self.known_enemy_structures) > 0:
   return random.choice(self.known_enemy_structures)
  else:
   return self.enemy_start_locations[0]

 async def attack(self):
  # {UNIT: [n to fight, n to defend]}
  aggressive_units = {VOIDRAY: [8, 3]}


  for UNIT in aggressive_units:
   for s in self.units(UNIT).idle:
    await self.do(s.attack(self.find_target(self.state)))
   if len(self.known_enemy_units) > 0:
    for s in self.units(UNIT):
     if not s.is_idle:
      if s.order_target not in self.known_enemy_units:
       await self.do(s.attack(self.find_target(self.state)))

 async def defend(self):
  nexus_distance = self.units(NEXUS).furthest_distance_to(self.game_info.map_center)
  furthest_nexus = self.units(NEXUS).furthest_to(self.game_info.map_center).position
  if (len(self.known_enemy_units) > 0 and (self.known_enemy_units.closest_distance_to(furthest_nexus)) < nexus_distance) or self.supply_used > 100:
   await self.attack()
  else:
   #defend_nexus = self.units(NEXUS).furthest_to(nexus.position)
   for unit in self.units(VOIDRAY):
    await self.do(unit.move(self.units(NEXUS).closest_to(self.game_info.map_center).position))



run_game(maps.get("AbyssalReefLE"), [
    Bot(Race.Protoss, ExifienceBot()),
    Computer(Race.Terran, Difficulty.Hard)
    ], realtime=False)
