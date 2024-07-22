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
                          f"{condition_info['condition']:04x}" + "\033[0m")
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
            [ { 'name': "Selios", 'text_index': 0 } ],
            [ { 'name': "Runan", 'text_index': 1 } ],
            [ { 'name': "Roh", 'text_index': 2 }, { 'name': "Sonia", 'text_index': 4 } ],
            [ { 'name': "Gail", 'text_index': 3 } ]
        ]
        self._current_leader_index = 0
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

        self._locators = {}
        condition_set = set()
        for key in self._key_list:
            key_addr = int(key, base=16)
            current_text = self._get_raw_translation(key)

            encoded_event, _, locators = encode_event(current_text)
            locators[key_addr] = 0

            for locator_addr, locator_event_offset in locators.items():
                self._locators[locator_addr] = { 'key': key_addr, 'offset': locator_event_offset }

                instructions = disassemble_event(encoded_event, key_addr, key_addr + locator_event_offset)
                for instruction in instructions:
                    if 'code' in instruction and instruction['code'] in [0x11, 0x12]:
                        condition_set.add(int.from_bytes(instruction['data'], byteorder='little'))

        self._condition_list = [ { 'condition': cond, 'state': False } for cond in sorted(condition_set) ]
        self._focused_condition_index = 0

        self.load_translation(0)


    def load_translation(self, index):
        self._display_index = index
        self._displayed_key = self._key_list[self._display_index]

        self._formatted_translation = [ [] ]

        current_line = ""
        current_key = self._displayed_key
        current_key_addr = int(current_key, base=16)

        current_input = self._get_raw_translation(current_key)
        encoded_input, _, _ = encode_event(current_input)
        event_iter = iter(disassemble_event(encoded_input, current_key_addr, current_key_addr))

        current_conditional_result = None

        for condition_info in self._condition_list:
            condition_info['used_in_current_line'] = False

        call_stack = []

        while True:
            instruction = next(event_iter, None)

            if instruction is None:
                break
            elif 'text' in instruction:
                current_line += instruction['text']
            else:
                code = instruction['code']
                data = instruction['data']
                if code == 0x00: # End
                    break
                elif code == 0x01: # Newline
                    self._formatted_translation[-1].append(current_line)
                    current_line = ""
                elif code == 0x05: # New page
                    self._formatted_translation[-1].append(current_line)
                    current_line = ""
                    self._formatted_translation.append([])
                elif code == 0x08: # Clear window
                    pass

                # Colors
                elif code == 0x04: # Reset color
                    current_line += "\033[0m"
                elif code == 0x1c: # Green
                    current_line += "\033[92m"
                elif code == 0x1e: # Yellow
                    current_line += "\033[93m"

                # Text insertion codes
                elif code == 0x09: # Insert character name
                    character_index = int.from_bytes(data, byteorder='little')
                    current_line += "\033[93m"
                    current_line += self.get_character_info(character_index)['name']
                    current_line += "\033[0m"
                elif code == 0x0e: # Insert item name
                    current_line += "\033[93m"
                    current_line += "Leather Shield"
                    current_line += "\033[0m"

                # Control flow
                elif code in [0x06, 0x07, 0x0a, 0x0d]: # Return, return with newline, two other return codes
                    if code == 0x07:
                        self._formatted_translation[-1].append(current_line)
                        current_line = ""

                    if len(call_stack) > 0:
                        return_info = call_stack.pop()
                        current_key = return_info['key']
                        event_iter = return_info['iter']
                    else:
                        break
                elif code == 0x0f: # Jump
                    call_addr = int.from_bytes(data, byteorder='little')

                    if current_conditional_result != False:
                        locator_info = self._locators[call_addr]
                        instruction_list = self._get_translation_instructions(locator_info['key'], locator_info['offset'])
                        event_iter = iter(instruction_list)
                    current_conditional_result = None
                elif code == 0x10: # Call
                    call_addr = int.from_bytes(data, byteorder='little')

                    locator_info = self._locators[call_addr]
                    call_stack.append( { 'key': current_key, 'iter': event_iter } )
                    instruction_list = self._get_translation_instructions(locator_info['key'], locator_info['offset'])
                    event_iter = iter(instruction_list)

                elif code == 0x11 or code == 0x12: # If (negated), if
                    inverted = code == 0x11
                    flag = int.from_bytes(data, byteorder='little')

                    for condition in self._condition_list:
                        if condition['condition'] == flag:
                            condition['used_in_current_line'] = True
                            current_conditional_result = (not condition['state'] if inverted else condition['state'])
                            break
                elif code == 0x16: # Call based on current leader
                    leader_info = self.get_character_info(self._current_leader_index)

                    call_addr = int.from_bytes(data[leader_info['text_index']*2:leader_info['text_index']*2 + 2], byteorder='little')

                    current_line += "\033[93m"
                    current_line += leader_info['name']
                    current_line += "\033[0m"
                    self._formatted_translation[-1].append(current_line)
                    current_line = ""

                    locator_info = self._locators[call_addr]
                    call_stack.append( { 'key': current_key, 'iter': event_iter } )
                    instruction_list = self._get_translation_instructions(locator_info['key'], locator_info['offset'])
                    event_iter = iter(instruction_list)

                elif code in [0x0c, 0x13, 0x14, 0x15]: # Play sound, clear flag, set flag, call asm routine
                    pass
                else:
                    current_line += f"<X{instruction['code']:02x}{instruction['data'].hex()}>"

            while len(re.sub("\033\[[0-9]+m", "", current_line)) >= 34:
                self._formatted_translation[-1].append(current_line[0:34])
                current_line = current_line[34:]

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
        trans_info = self._trans[key]
        current_text = trans_info['translation'] if 'translation' in trans_info else trans_info['original']
        current_text = current_text.replace("\r", "")
        return current_text


    def _get_translation_instructions(self, translation_key, event_offset):
        translation = self._get_raw_translation(f"{translation_key:04x}")
        encoded, _, _ = encode_event(translation)
        instruction_list = disassemble_event(encoded, translation_key, translation_key + event_offset)
        return instruction_list


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