# English translation patch for *Dragon Slayer: The Legend of Heroes* (PC-98)

*Dragon Slayer: The Legend of Heroes*, released in Japan in 1989 for various platforms, was the sixth game in the Dragon Slayer series and the first game in the Legend of Heroes series.  While it did receive an official English release on the TurboGrafx-CD, that version had some changes, including minor censorship and fairly arbitrary changes to the names of characters and places. This patch for the PC-98 version attempts to stay as true to the original text of the game as possible.

## Applying the patch

The patch files are intended to be applied to NFD dumps of the game disks. Checksums for the source disks are provided below (but, for the Scenario Disk in particular, this checksum may vary depending on what save data is on the disk).

| Disk          | CRC32    | SHA-1                                    |
|---------------|----------|------------------------------------------|
| Event Disk    | B859CBA0 | 9147706CD69BA17FCC4FFD96F28E49E348067F3B |
| Program Disk  | A35403C1 | 0FA8CCE2FDCFDAB1FBBC0EDBB41916885418073E |
| Scenario Disk | 63F69452 | B9B9F8BBD1B22274F8F19E50D7B240A878C8E71B |

The patch files are simply distributed in IPS format. There are a plethora of IPS patching tools online, so choose your favorite for your platform. (Romhacking.net has an [easy online tool](https://www.romhacking.net/patch/).) Remember that IPS patches do not perform any error checking, so applying these patches to any file other than NFD disks with the correct sector order will likely produce garbage.

This release also includes a small patch for the Scenario Disk that disables some previously undocumented copy protection behavior during Chapter 4 which only seems to occur on real hardware. (If you're playing on emulator, you shouldn't need to worry about this.) The copy protection patch can be applied either before or after the Scenario Disk translation patch. Without this patch, you will basically be stuck waiting forever for a certain egg to hatch during Chapter 4.

## Game manual

This is general information about how to play the game, adapted from the [original manual](https://archive.org/details/Dragon_Slayer_The_Legend_of_Heroes_Manual/) which players would have had available.

### Story

A long time ago... or was it in the distant future?

Either way, there was a fertile world called Isilartha,
whose people lived and thrived amid its natural abundance.

In the center of Isilartha, the island of Romwoll and the much smaller island Sarthuai made up the kingdom of Farleyn. It was a poor nation, with little land and no exports of note. But its people lived their simple lives with few complaints. Under the reign of their kind king Asuel, they passed their days in peace.

One night, unforseen tragedy struck its capital of Rudia. A horde of monsters easily stormed the castle, through gates which had somehow been left unbarred. The castle soldiers, who had never before seen a monster, were taken by surprise and drawn into a pitched melee. But they held their own until daybreak, and ultimately, the attackers
were dispersed.

The people celebrated, but their joy was short-lived.

For they soon learned that King Asuel had been killed.

The king's heir, Prince Selios, was only six years old. Chancellor Achdam, the only witness to Asuel's death, announced that the dying king had named him regent until the prince's coronation at the age of sixteen.

Until then, the young prince would be raised in the village of Eluasta, on Sarthuai Isle.

And so ten years passed...

### Character introduction

* **Selios** (15, male) - The prince of the Kingdom of Farleyn. At the age of six, he lost his father in a monster attack, and is now being raised in the village of Eluasta until he takes the throne at the age of 16, in two months' time.
* **Runan** (30, male) - A traveling mendicant who joined the resistance against the regent Achdam while visiting the Kingdom of Farleyn. He will later work alongside Selios.
* **Ro** (22, male) - A young man who lives in the village of Crus in the Kingdom of Farleyn. A frivolous person who spends his days galavanting about, but is capable of using powerful spells.
* **Gail** (26, male) - A man who opposed Achdam and was forced into labor in the Belga Mine. His true homeland and identity are unknown.
* **Sonia** (20, female) - The daughter of Alon, the leader of the resistance. A strong-minded, strong-willed woman.

### Starting the game

To view the opening cinematic, insert the Event Disk into drive 1 and boot the system.

If you hold the [SHIFT] key while booting, the Utility Menu will be shown instead. This menu allows you to start the game without viewing the demo, as well as configuring game difficulty, system hardware, and other settings.

The effect of the difficulty setting is to change the EXP and gold awarded from defeating monsters. Players who really, really like grinding are encouraged to change this setting.

* **Easy** - Uses the default settings.
* **Normal** - 75% of the default values.
* **Hard** - 50% of the default values.
* **HELL** - 25% of the default values.

To continue a previously saved game, insert the Program Disk into drive 1 and the Scenario Disk into drive 2. The Scenario Disk is used to save in-game data, so ensure that it is writable.

### Game controls

Use the numpad/ten-key to move your character in the game and to navigate menus. [4] [6] will move left and right; [2] [8] will move up and down. If you hold down the [SPACE] key while moving, you will not trigger conversations when touching other characters.

[SPACE] [RETURN] [XFER] are used to select an option in menus.

[ESC] [SHIFT] [NFER] are used to show the in-game menu, or to exit a menu without making a selection.

You can also control the game with a joystick or a controller. The directional pad is used for movement. Button 1 is used to select an option; button 2 is used to show the menu or to cancel selection.

To save time when navigating menus, the function keys [F1]~[F10] can be used as shortcut keys for commonly-used commands. A reference for these functions can be shown during gameplay by setting the "Function keys" option in the utility menu to "Show".

* **[F1]** - Use a Lens of Joshua.
* **[F2]** - Use the Warp spell.
* **[F3]** - Use spells.
* **[F4]** - Use items.
* **[F5]** - Change equipment.
* **[F6]** - Show the system configuration menu.
* **[F7]** - Show the combat configuration menu.
* **[F8]** - Save.
* **[F9]** - Load.
* **[F10]** - Load from RAM.

### Status effects

* **Defending (Θ)** - Indicates that a combatant is protected. This is shown if a party member chooses the "Defend" option in combat.
* **Reflect (≪)** - Indicates that enemy spells are being deflected from a character due to the Reparc spell.
* **Poison (Ｘ)** - Indicates that a combatant is poisoned. After a few turns, this party member will be unconscious.
* **Sleep (Ｚ)** - Indicates that a combatant has been put to sleep. This character will take damage easily.
* **Confusion (？)** - Indicates that a combatant has lost their senses and is acting randomly. They will attack and heal without distinguishing friend from foe.
* **Silence (…)** - Indicates that a combatant is unable to speak and cannot use spells.
* **Unconscious** - Indicates that a combatant's HP has been reduced to 0 and can no longer participate in battle.

### Spell list

Although your characters will know a few spells from the beginning, you will need to learn more powerful spells from people you meet in towns.

| Spell name    | Effect strength               | Description |
|---------------|-------------------------------|-------------|
| Flam [1-5]    | 20 / 50 / 100 / 200 / 500     | Damages an enemy with a fireball. (But will heal monsters whose power derives from fire.) |
| Igna [1-5]    | 20 / 50 / 100 / 200 / 500     | Damages an enemy with a lightning strike. (But will heal monsters whose powers derives from electricity.) |
| Hura [1-5]    | 20 / 50 / 100 / 200 / 500     | Damages an enemy with an ice arrow. (But will heal monsters whose power derives from cold.) |
| Obis [1-3]    | ⅓ / ½ / ⅔                     | Has a chance of knocking out an enemy instantly. (But has no effect on monsters which are formless or lifeless.) |
| Suctas [1-4]  | 20 / 50/ 100 / 200            | Drains HP out of an enemy and into the caster. (But be wary of monsters who have HP wholly unlike that of humans.) |
| Sucto [1-4]   | 5 / 12 / 25 / 50              | Drains MP out of an enemy and into the caster. (But this is useless against enemies with no natural magic.) |
| Danam [1-4]   | 20 / 50 / 100 / 200           | Reduces an enemy's defense. (This spell is an effective way to increase the damage you deal against enemies with high defense.) |
| Hebetar [1-3] | 5 / 12 / 15                   | Reduces an enemy's speed. (Enemies will get fewer attacks, giving you the chance to attack them.) |
| Serento [1-3] | ⅓ / ½ / ⅔                     | Makes an enemy unable to speak and unable to use spells. (This also prevents enemies from screeching or calling for help.) |
| Papepia [1-3] | ⅓ / ½ / ⅔                     | Confuses an enemy and makes them unable to distinguish friend from foe. (But they will eventually return to their senses.) |
| Hoa [1-3]     | ⅓ / ½ / ⅔                     | Puts an enemy to sleep for 3 turns. (All attacks against a sleeping opponent will be critical hits.) |
| Poizo [1-3]   | 6 turns / 5 turns / 4 turns   | Bathes the enemy in a poison which will knock them out after a certain number of turns. |
| Sylis 1       | -                             | Prevents everyone in the area from using spells. |
| Impas [1-4]   | 20 / 50 / 100 / 200           | Increases a party member's attack power. (Greatly increases the damage you deal. Useful against enemies with high HP, high defense, or in long battles.) |
| Teuto [1-4]   | 20 / 50 / 100 / 200           | Increases a party member's defense. (Makes it harder to damage the target. Useful against enemies with high attack power, or when your HP is low.) |
| Sela [1-3]    | 10 / 25 / 50                  | Increaes a party member's speed. (This is useful because it increases the number of times you attack.) |
| Reparc1 | -   | Deflects all spells that target you back at your opponent. |
| Res [1-4]     | 100 / 250 / 500 / 1000 / 2500 | Restores a party member's HP. (Keep an eye on your HP; this won't work on characters who run out of HP and fall unconscious.)   |
| Regina1       | -                             | Neutralizes poison and returns the target to normal. |
| Lefe1         | -                             | Wakes up an unconscious ally. They will have 1 HP upon awakening. |
| Warp1         | -                             | Warps you instantly to the last town you left. It can be used inside caves and towers for a quick escape. |
| Warp2         | -                             | Warps you instantly to any town you have visited. It cannot be used inside caves or towers. |

### Item list

Your inventory is limited to 28 items, not counting any items which your characters have equipped.

#### Weapons

| Name           | Cost   | Effect     |
|----------------|-------:|------------|
| Knife          | 100    | Attack +15 |
| Short Sword    | 200    | Attack +25 |
| Copper Sword   | 500    | Attack +50 |
| Iron Spear     | 1000   | Attack +90 |
| Iron Sword     | 2000   | Attack +100 |
| Steel Spear    | 4000   | Attack +180 |
| Steel Sword    | 6000   | Attack +200 |
| Silver Sword   | 12000  | Attack +260 |
| Crystal Spear  | 20000  | Attack +300 |
| Crystal Sword  | 25000  | Attack +320 |
| Platinum Spear | 35000  | Attack +360 |
| Royal Sword    | -      | Attack +400 |
| Platinum Sword | 50000  | Attack +400 |
| Ceramic Sword  | 80000  | Attack +430 |
| Holy Sword     | 100000 | Attack +460 |
| Diamond Sword  | 150000 | Attack +500; vulnerable to heat |
| Hero Sword     | 300000 | Attack +600 |
| Holy Staff     | 10000  | Attack +5; ⅓ chance of putting the target to sleep |
| Silver Staff   | 10000  | Attack +5; ⅓ chance of knocking out the target |
| Fire Staff     | 10000  | Attack +5; inflicts around 100 points of fire damage to the target |
| Crystal Staff  | 20000  | Attack +5; drains 100 HP from the target |
| Thunder Staff  | 10000  | Attack +5; inflicts around 100 points of lightning damage to the target |
| Ice Staff      | 10000  | Attack +5; inflicts around 100 points of ice damage to the target |
| Diamond Staff  | 130000 | Attack +5; drains 200 HP from the target |

#### Armor

| Name           | Cost   | Effect     |
|----------------|-------:|------------|
| Clothes        | 100    | Defense +5 |
| Travel Clothes | 200    | Defense +10 |
| Leather Armor  | 350    | Defense +20 |
| Copper Armor   | 500    | Defense +30 |
| Chain Mail     | 1000   | Defense +40 |
| Iron Armor     | 2500   | Defense +60 |
| Steel Armor    | 5000   | Defense +80 |
| Silver Armor   | 10000  | Defense +100 |
| Crystal Armor  | 20000  | Defense +120 |
| Royal Armor    | -      | Defense +140 |
| Platinum Armor | 40000  | Defense +140 |
| Holy Armor     | 70000  | Defense +160 |
| Diamond Armor  | 100000 | Defense +200; vulnerable to heat |
| Battle Suit    | 300000 | Defense +400 |
| Silk Robe      | 4000   | Defense +50; deflects enemy spells if the wearer defends in battle |
| Healing Robe   | 6000   | Defense +50; restores HP if the wearer defends in battle |
| Leather Shield | 150    | Defense +5 |
| Copper SHield  | 400    | Defense +15 |
| Iron Shield    | 1200   | Defense +40 |
| Steel Shield   | 4000   | Defense +60 |
| Silver Shield  | 8000   | Defense +80 |
| Crystal Shield | 18000  | Defense +100 |
| Platinum Shld  | 35000  | Defense +120 |
| Royal Shield   | -      | Defense +120 |
| Holy Shield    | 60000  | Defense +140 |
| Diamond Shield | 80000  | Defense +160; vulnerable to heat |
| Ancient Shield | 200000 | Defense +200 |

#### Items

| Name           | Cost   | Effect     |
|----------------|-------:|------------|
| Opna Ring      | 3000   | Attack +100 when equipped |
| Tut Ring       | 2000   | Defense +50 when equipped |
| Quick Ring     | 3000   | Speed +10 when equipped |
| Luck Ring      | 3000   | Luck +50 when equipped |
| Res Leaf       | 50     | Restores 500 HP |
| Res Root       | 500    | Restores 1000 HP |
| Bis Fruit      | 7000   | Fully restores MP |
| Antidote Herb  | 5      | Neutralizes poison |
| Smelling Salt  | 50     | Awakens an unconscious character with 1 HP |
| Bottle of Rum  | 1000   | Awakens an unconscious character with full HP |
| Elixir         | 50000  | Awakens an unconscious character with full HP and MP |
| Torch          | 5      | Temporarily illuminates a dark cave; can use several at the same time
| Reveal Chime   | 200    | Makes monsters outdoors temporarily visible |
| Eye of Joshua  | 10     | Shows a map of the current area; can scroll when outdoors |
| Lens of Joshua | 2000   | " |
| Warp Feather   | 100    | Returns you to the last town you left; can be used in caves and towers |
| Warp Wing      | 500    | Warps you to any place you have visited; cannot be used in caves or towers
| Black Powder   | 1000   | Inflicts 500 damange on an enemy when used in battle |
| Sleepweed      | -      | ⅔ chance of putting an enemy to sleep when used in battle

### Game over options

When your party is defaeated in battle, you will have the following options.

* **Previous town** - Returns you to the last town you exited. All party members will have their HP set to 1, but will retain their current items, gold, and EXP.
* **Restart battle** - Returns you to the moment when you entered the battle and allows you to retry it.
* **Load a save** - Restarts from a previous save file. (If you choose the automatic RAM save from the bottom of this menu, the effect will be the same as "Restart battle.")

## Development

### Building the patch

Open ds6_patch.conf and make sure that the `Original...` fields point to your original .nfd disk images. Also make sure that `NasmPath` points to the nasm executable.

Run `python build_patch.py`. This should produce .ips patches for each disk, as well as a patched copy of each disk, in the "build" subfolder.

### Modifying translations

You can use e.g. `python test_translation.py 10.00.20` to attempt to process a single CSV file and check for errors. (Typically, the errors you'll see are due to the translated text being too long to fit into the original disk sectors.)

Using e.g. `python preview_text.py 10.00.20` will bring up a quick preview display that will let you confirm that the text fits the in-game dialog window correctly. Up/down arrow keys change the current page or selection. Tab navigates from the text window to the flag selection panes; space toggles a flag on and off.

`python import_from_tpp.py` and `python export_to_tpp.py` will allow you to sync the translation CSVs with a Translator++ project. Running the "import" script will generate a file called "ds6.trans" in the current directory. The "export" script will write any changes made in that file back to the CSVs.

## Additional notes

Thanks to the [PC-98 Discord server](https://discord.gg/28FX2YMCeT) for tolerating the occasional dumb question about PC-98 hardware. Thanks to my Twitch chat for nudging me repeatedly to get this thing finished.

This game has an awful lot of text and a lot of paths to experiment with, so it's quite likely there are some minor text bugs that I haven't spotted in my testing. If you notice any bugs, they can be reported in the [GitHub project](https://github.com/nleseul/ds6_pc98_trans).

My Japanese is still fairly medicore, so there's a reasonable chance that my interpretation of one or more lines in the game are completely wrong. If something doesn't make sense, it's probably my fault. If you want to compare the translation to the original game text, you can always cross-reference the translation data files stored in the aforementioned GitHub project.

If you appreciate this project and if you feel so inclined, I do have a donation link set up on [Ko-Fi](https://ko-fi.com/nleseul).