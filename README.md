# OSRS Python Utils SDK

A collection of scripts that can be imported into any other project so that I can use them in bigger projects

enable the api from the plugin hub. just use a release.exe version and make sure your weapon is in the first slot of the inventory at all times.

use parameters:
`-y` = yolo mode
`--switches=<amount>` = from slots in the two first columns of each row in your inventory

use `.` on keyboard to start combat loop
use `q` on keyboard during combat loop for when magic phase is activated to switch gear
use `w` for the ranged phase and use `e` for the melee phase (not much will happen)

use `ctrl+.` to stop the combat loop

### combat Loop:
1. Uses food and combo food to heal up
2. teleports out on the literal last possible second. but remember
3. IT WILL NOT RISK YOUR HEALTH BELOW 41 (max hit) IF FOOD IS NONEXISTENT
4. Enables switching hotkeys for moments where you need to chat/search or whatever else on your computer to not interfere with your actions.
