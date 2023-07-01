import configparser
import culour
import curses
import re
import sys

from ds6_util import *

class Pane:
    def __init__(self, model, x, y, width, height):
        self._model = model
        self._win = curses.newwin(height, width, y, x)
        self._win.keypad(True)

    def handle_input(self):
        ch = self._win.getch()

        return ch

    def draw(self, is_focused):
        self._win.refresh()

class TextPreviewPane(Pane):
    def __init__(self, model, x, y, width, height):
        super().__init__(model, x, y, width, height)
        
        self._display_page = 0

    def handle_input(self):
        ch = super().handle_input()

        if ch == curses.KEY_LEFT:
            self._model.load_translation((self._model.display_index - 1) % self._model.key_count)
            self._display_page = 0
        elif ch == curses.KEY_RIGHT:
            self._model.load_translation((self._model.display_index + 1) % self._model.key_count)
            self._display_page = 0
        elif ch == curses.KEY_DOWN:
            self._display_page = min(self._display_page + 1, len(self._model.formatted_translation) - 1)
        elif ch == curses.KEY_UP:
            self._display_page = max(self._display_page - 1, 0)

        return ch


    def draw(self, is_focused):

        if self._display_page >= len(self._model.formatted_translation):
            self._display_page = len(self._model.formatted_translation) - 1

        self._win.clear()
        self._win.addstr(0, 0, f"Text {self._model.displayed_key} ({self._model.display_index+1}/{self._model.key_count})", curses.A_REVERSE if is_focused else curses.A_NORMAL)
        self._win.addstr(1, 1, f"Page ({self._display_page+1}/{len(self._model.formatted_translation)})")

        for line_index, line in enumerate(self._model.formatted_translation[self._display_page]):
            culour.addstr(self._win, 3 + line_index, 1, line)

        super().draw(is_focused)


class ConditionListPane(Pane):
    def __init__(self, model, x, y, width, height):
        super().__init__(model, x, y, width, height)
        
        self._focus_index = 0

    
    def handle_input(self):
        ch = super().handle_input()

        if ch == curses.KEY_DOWN:
            self._focus_index = (self._focus_index + 1) % len(self._model.condition_list)
        elif ch == curses.KEY_UP:
            self._focus_index = (self._focus_index - 1) % len(self._model.condition_list)
        elif ch == ord(' '):
            self._model.condition_list[self._focus_index]['state'] = not self._model.condition_list[self._focus_index]['state']
            self._model.load_translation(self._model.display_index)

        return ch

        
    def draw(self, is_focused):
        self._win.clear()

        self._win.addstr(0, 0, "Conditions", curses.A_REVERSE if is_focused else curses.A_NORMAL)

        for condition_index, condition_info in enumerate(self._model.condition_list):
            if self._focus_index == condition_index:
                self._win.addstr(1 + condition_index, 1, ">")
            culour.addstr(self._win, 1 + condition_index, 3, ("\033[94m" if not condition_info['used_in_current_line'] else "") + 
                          condition_info['condition'] + "\033[0m")
            if condition_info['state']:
                self._win.addstr(1 + condition_index, 8, "*")

        super().draw(is_focused)


class ActiveLeaderPane(Pane):
    def __init__(self, model, x, y, width, height):
        super().__init__(model, x, y, width, height)
        
        self._focus_index = 0


    def handle_input(self):
        ch = super().handle_input()

        if ch == curses.KEY_DOWN:
            self._focus_index = (self._focus_index + 1) % self._model.character_count
        elif ch == curses.KEY_UP:
            self._focus_index = (self._focus_index - 1) % self._model.character_count
        elif ch == curses.KEY_LEFT or ch == curses.KEY_RIGHT:
            self._model.roh_in_party = not self._model.roh_in_party
            self._model.load_translation(self._model.display_index)
        elif ch == ord(' '):
            self._model.current_leader_index = self._focus_index
            self._model.load_translation(self._model.display_index)

        return ch


    def draw(self, is_focused):
        self._win.clear()

        self._win.addstr(0, 0, "Leader", curses.A_REVERSE if is_focused else curses.A_NORMAL)

        for character_index in range(self._model.character_count):
            character_info = self._model.get_character_info(character_index)

            if self._focus_index == character_index:
                self._win.addstr(1 + character_index, 1, ">")

            self._win.addstr(1 + character_index, 3, character_info['name'] +
                          (" *" if character_index == self._model.current_leader_index else ""))

        super().draw(is_focused)


class Model:
    def __init__(self, sector_key):
        configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
        configfile.read("ds6_patch.conf")
        self._config = configfile['DEFAULT']

        self._party_info = [
            [ { 'name': "Selios", 'leader_index': 0 } ],
            [ { 'name': "Runan", 'leader_index': 1 } ],
            [ { 'name': "Roh", 'leader_index': 2 }, { 'name': "Sonia", 'leader_index': 4 } ],
            [ { 'name': "Gail", 'leader_index': 3 } ]
        ]
        self._current_leader_index = 1
        self._roh_in_party = False

        self.load_sector(sector_key)

    
    def load_sector(self, sector_key):
        self._sector_key = sector_key
        with open(self._config['OriginalScenarioDisk'], 'rb') as scenario_disk:
            scenario_directory = get_scenario_directory(scenario_disk)
            combat_directory = get_combat_directory(scenario_disk)

            if sector_key in scenario_directory:
                self._trans = load_translations_csv(f"csv/Scenarios/{format_sector_key(sector_key)}.csv")
            elif sector_key in combat_directory:
                self._trans = load_translations_csv(f"csv/Combats/{format_sector_key(sector_key)}.csv")
            else:
                raise Exception(f"Sector key {format_sector_key(sector_key)} is neither a scenario nor a combat.")

        self._key_list = list(self._trans.keys())

        condition_set = set()
        for key in self._key_list:
            loc = 0
            current_text = self._trans[key]['translation'].replace("\r", "")
            while True:
                loc = current_text.find("<IF", loc)
                if loc < 0:
                    break
                else:
                    if current_text[loc+3:loc+7] == "_NOT":
                        loc += 4
                    condition_set.add(current_text[loc+3:loc+7])
                    loc += 8

        self._condition_list = [ { 'condition': cond, 'state': False } for cond in sorted(condition_set) ]
        self._focused_condition_index = 0

        self._locators = {}
        for key in self._key_list:
            self._locators[key] = { 'key': key, 'loc': 0}

            loc = 0
            current_text = self._trans[key]['translation'].replace("\r", "")
            while True:
                loc = current_text.find("<LOC", loc)
                if loc < 0:
                    break
                else:
                    self._locators[current_text[loc+4:loc+8]] = { 'key': key, 'loc': loc }
                    loc += 9
                
        self.load_translation(0)


    def load_translation(self, index):
        self._display_index = index
        self._displayed_key = self._key_list[self._display_index]
        
        self._formatted_translation = [ [] ]

        current_line = ""
        current_key = self._displayed_key
        
        current_input = self._get_raw_translation(current_key)
        loc = 0

        current_conditional_result = None

        for condition_info in self._condition_list:
            condition_info['used_in_current_line'] = False

        call_stack = []

        while loc < len(current_input):
            if current_input[loc:].startswith("<X"):
                hex_bytes = ""
                loc += 2
                while current_input[loc] != ">":
                    hex_bytes += current_input[loc]
                    loc += 1
                loc += 1
            
                value = int(hex_bytes, base=16)
                if value == 0x06 or value == 0x0a or value == 0x0d:
                    break
                elif value == 0x04:
                    current_line += "\033[0m"
                elif value == 0x1c:
                    current_line += "\033[92m"
                elif value == 0x1e:
                    current_line += "\033[93m"
                elif value == 0x0e:
                    current_line += "Leather Shield"
                else:
                    pass
            
            elif current_input[loc:].startswith("<JUMP"):
                call_addr = current_input[loc+5:loc+9]
                loc += 10
            
                if current_conditional_result != False:
                    locator_info = self._locators[call_addr]
                    current_key = locator_info['key']
                    current_input = self._get_raw_translation(current_key)
                    loc = locator_info['loc']
                current_conditional_result = None
        
            elif current_input[loc:].startswith("<CALL"):
                call_addr = current_input[loc+5:loc+9]
                loc += 10

                call_stack.append( { 'key': current_key, 'loc': loc } )

                locator_info = self._locators[call_addr]
                current_key = locator_info['key']
                current_input = self._get_raw_translation(current_key)
                loc = locator_info['loc']
            
            elif current_input[loc:].startswith("<ASM"):
                loc += 4
                if current_input[loc:].startswith("_NORET"):
                    loc += 6
                    break
                loc += 5
            
            elif current_input[loc:].startswith("<LEADER"):
                loc += 7
                call_addr = current_input[loc + self._current_leader_index*5:loc + self._current_leader_index*5 + 4]
                loc += 25

                current_line += "\033[93m"
                current_line += self.get_character_info(self._current_leader_index)['name']
                current_line += "\033[0m"
                self._formatted_translation[-1].append(current_line)
                current_line = ""

                call_stack.append( { 'key': current_key, 'loc': loc } )

                locator_info = self._locators[call_addr]
                current_key = locator_info['key']
                current_input = self._get_raw_translation(current_key)
                loc = locator_info['loc']
                
            elif current_input[loc:].startswith("<IF"):
                loc += 3
                inverted = False
                if current_input[loc:].startswith("_NOT"):
                    inverted = True
                    loc += 4
                flag = current_input[loc:loc+4]
                loc += 5

                for condition in self._condition_list:
                    if condition['condition'] == flag:
                        condition['used_in_current_line'] = True
                        current_conditional_result = condition['state']
                        break
        
            elif current_input[loc:].startswith("<CLEAR"):
                flag = int(current_input[loc+6:loc+10], base=16)
                loc += 11
            
            elif current_input[loc:].startswith("<SET"):
                flag = int(current_input[loc+4:loc+8], base=16)
                loc += 9
            
            elif current_input[loc:].startswith("<RET_IL>"):
                if len(call_stack) > 0:
                    return_info = call_stack.pop()
                    current_key = return_info['key']
                    current_input = self._trans[current_key]['translation'].replace("\r", "")
                    loc = return_info['loc']
                else:
                    break
            
            elif current_input[loc:].startswith("<RETN>"):
                self._formatted_translation[-1].append(current_line)
                current_line = ""
            
                if len(call_stack) > 0:
                    return_info = call_stack.pop()
                    current_key = return_info['key']
                    current_input = self._trans[current_key]['translation'].replace("\r", "")
                    loc = return_info['loc']
                else:
                    break
            
            elif current_input[loc:].startswith("<CH"):
                character_index = int(current_input[loc+3:loc+4])
                loc += 5
                current_line += "\033[93m"
                current_line += self.get_character_info(character_index)['name']
                current_line += "\033[0m"
            
            elif current_input[loc:].startswith("<LOC"):
                loc += 9
            
            elif current_input[loc:].startswith("<N>\n"):
                self._formatted_translation[-1].append(current_line)
                current_line = ""
                loc += 4
            
            elif current_input[loc:].startswith("<WAIT>\n"):
                self._formatted_translation[-1].append(current_line)
                current_line = ""
                loc += 7
            
            elif current_input[loc:].startswith("<PAGE>\n"):
                self._formatted_translation[-1].append(current_line)
                current_line = ""
                self._formatted_translation.append([])
                loc += 7
            
            elif current_input[loc:].startswith("<END>\n"):
                break
            
            elif current_input[loc:].startswith("<"):
                raise Exception("Unknown tag " + current_input[loc:loc+10] + "!")

            elif current_input[loc:].startswith("\n\n"):
                loc += 2
                self._formatted_translation[-1].append(current_line)
                current_line = ""
                self._formatted_translation.append([])

            elif current_input[loc:].startswith('\n'):
                loc += 1
                self._formatted_translation[-1].append(current_line)
                current_line = ""

            else:
                current_line = current_line + current_input[loc]
                loc += 1

            if len(re.sub("\033\[[0-9]+m", "", current_line)) >= 34:
                self._formatted_translation[-1].append(current_line)
                current_line = ""

            if len(self._formatted_translation[-1]) >= 4:
                self._formatted_translation.append([])
    
        if len(current_line) > 0:
            self._formatted_translation[-1].append(current_line)

    
    @property
    def display_index(self):
        return self._display_index


    @property
    def displayed_key(self):
        return self._displayed_key


    @property
    def key_count(self):
        return len(self._key_list)
            
            
    @property
    def formatted_translation(self):
        return self._formatted_translation


    @property
    def condition_list(self):
        return self._condition_list


    @property
    def character_count(self):
        return len(self._party_info)


    @property
    def current_leader_index(self):
        return self._current_leader_index
    @current_leader_index.setter
    def current_leader_index(self, value):
        self._current_leader_index = value


    @property
    def roh_in_party(self):
        return self._roh_in_party
    @roh_in_party.setter
    def roh_in_party(self, value):
        self._roh_in_party = value


    def get_character_info(self, character_index):
        if character_index == 2 and not self._roh_in_party:
            return self._party_info[character_index][1]
        else:
            return self._party_info[character_index][0]

            
    def _get_raw_translation(self, key):
        return self._trans[key]['translation'].replace("\r", "")
    

def curses_main(screen, argv):

    sector_key_str = argv[0]
    match = re.search("^([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})$", sector_key_str)
    sector_key = (int(match.group(1), base=16), int(match.group(2), base=16), int(match.group(3), base=16))
    
    model = Model(sector_key)

    panes = [
        TextPreviewPane(model, 2, 1, 36, 8), 
        ConditionListPane(model, 40, 1, 10, 20),
        ActiveLeaderPane(model, 60, 1, 12, 20)]
    focused_pane_index = 0

    while True:

        screen.clear()

        for pane_index, pane in enumerate(panes):
            pane.draw(pane_index == focused_pane_index)

        focused_pane = panes[focused_pane_index]
        ch = focused_pane.handle_input()
        
        if ch == ord('\t'):
            focused_pane_index = (focused_pane_index + 1) % len(panes)
        elif ch == ord('q'):
            break

if __name__ == '__main__':
    curses.wrapper(curses_main, sys.argv[1:])