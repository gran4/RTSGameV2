from Buildings import *
from Player import *
from BackGround import *



ui_obj_info = {"Buildings":["Factory", "StoneWall", "Dormatory", "Metal Wall", "Raindeer Farm", "Work Shop", "BlackSmith", "Fire Station", "Material Depot", "Food Depot", "Igloo", "Encampment", "Research Shop", "Hospital", "Lumbermill", "Quary", "Farm", "Lab", "Snow Tower", "Pasture", "Pass", "Pebble Site"],
"People":["Person"],
"Boats":["Cannoe", "Viking Long Ship"]}

unlocked = {None:False, "Factory":False, "StoneWall":True, "Dormatory":False, "Metal Wall":False, "Raindeer Farm":False, "Work Shop":False, "BlackSmith":False, "Viking Long Ship":False, "Fire Station":True, "Material Depot":False, "Food Depot":False, "Igloo":True, "Bad Reporter":False, "Bad Gifter":False, "Encampment":True, "Research Shop":False, "Person":True, "Cannoe":False, 'Hospital':False, 'Lumbermill':False, 'Quary':False, "Farm":False, "Lab":False, "Snow Tower":False, "Pasture":False, "Pass":True, "Pebble Site":True, "Basic Enemy":True, "Privateer":True, "Enemy Swordsman":False, "Enemy Archer":False, "Enemy Arsonist":False, "Enemy Wizard":False}
objects = {"Factory":Factory, "StoneWall":StoneWall, "Dormatory":Dormatory, "Metal Wall":MetalWall, "Raindeer Farm":RaindeerFarm, "Work Shop":WorkShop, "BlackSmith":BlackSmith, "Viking Long Ship":VikingLongShip, "Fire Station":FireStation, "Material Depot":MaterialDepot, "Food Depot":FoodDepot, "Igloo":Igloo, "Bad Gifter":BadGifter, "Encampment":Encampment, 'Hospital':Hospital, "Bad Reporter":BadReporter, 'Lumbermill':Lumbermill, 'Quary':Quary, "Research Shop":ResearchShop, "Person":Person, "Farm":Farm, "Bad_Cannoe":Bad_Cannoe, "Lab":Lab, "Snow Tower":SnowTower, "Pass":Pass, "Pebble Site":PebbleSite}
requirements = {"Factory":{"metal":5}, "StoneWall":{"stone":1}, "Dormatory":{"wood":10, "stone":2}, "Metal Wall":{"metal":1}, "Raindeer Farm":{"food":50, "wood":5}, "Work Shop":{"wood":5, "stone":5}, "BlackSmith":{"wood":10, "stone":25}, "Viking Long Ship":{"wood":10}, "Fire Station":{}, "Material Depot":{"wood":5}, "Food Depot":{"wood":5}, "Igloo":{"wood":3}, "Encampment":{}, "Bad Gifter":{"toys":10}, "Bad Reporter":{}, "Research Shop":{"wood":5, "stone":2}, 'Hospital':{"wood":25}, 'Lumbermill':{"wood":10}, 'Quary':{"wood":15}, "Person":{"food":100}, "Farm":{"wood":15}, "Bad_Cannoe":{}, "Lab":{"wood":10, "stone":5}, "Snow Tower":{}, "Pasture":{"wood":3, "stone":1}, "Pass":{"wood":5}, "Pebble Site":{"wood":5}}
tiles = {"Factory":Land, "StoneWall":Land, "Dormatory":Land, "Metal Wall":Land, "Raindeer Farm":Land, "Work Shop":Land, "BlackSmith":Land, "Viking Long Ship":Sea, "Fire Station":Land, "Material Depot":Land, "Food Depot":Land, "Igloo":Land, "Encampment":Land, "Research Shop":Land, 'Hospital':Land, 'Lumbermill':Tree, 'Quary':Stone, "Person":Land, "Farm":Land, "Bad_Cannoe":Sea, "Lab":Land, "Snow Tower":Land, "Pasture":Land, "Pass":Stone, "Pebble Site":Stone}
times = {"Factory":20, "StoneWall":2, "Dormatory":10, "Metal Wall":5, "Raindeer Farm":0, "Work Shop":10, "BlackSmith":25, "Viking Long Ship":.2, "Fire Station":.2, "Material Depot":10, "Food Depot":5, "Igloo":5, 'Encampment':10, 'Research Shop':10, 'Hospital':15, 'Lumbermill':5, 'Quary':5, "Person":0, "Farm":10, "Bad_Cannoe":5, "Lab":10, "Snow Tower":10, "Pasture":5, "Pass":5, "Pebble Site":10}
max_length = {"Factory":2, "StoneWall":1, "Dormatory":2, "Metal Wall":3, "Raindeer Farm":1, "Work Shop":1, "BlackSmith":1, "Fire Station":1, "Material Depot":1, "Food Depot":1, "Igloo":1, "Encampment":1, 'Hospital':1, 'Lumbermill':1, 'Quary':2, "Research Shop":2, "Farm":1, "Lab":2, "Snow Tower":2, "Pass":1, "Pebble Site":1}

items_to_show = ["food", "wood", "stone", "metal", "science"]
item_weight = {"food":1, "wood":1, "stone":2, "metal":4}

#make each have alot so you can defualt to creative mode
prev_frame = {"food":1000, "wood":0, "stone":0, "metal":0}
descriptions = {
    "Bad Gifter":"Gives bad gifts      ",
    "Bad Reporter":"Gives bad reports      "
    }