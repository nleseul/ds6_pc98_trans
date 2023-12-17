import csv

from capstone import *
from capstone.x86 import *

def get_sector_info_nfd0(disk_image):
    sector_list = []

    disk_image.seek(0)
    if disk_image.read(0xe) != b'T98FDDIMAGE.R0':
        raise Exception("Unexpected disk format!")
    
    disk_image.seek(0x110)
    
    header_size = int.from_bytes(disk_image.read(0x4), byteorder='little')
    disk_image.read(0x1) # Write protect
    head_count = disk_image.read(0x1)[0]
    sector_size = None
    
    data_block_index = 0
    for data_block_header_index in range(163 * 26): # Hardcoded in data format
        disk_image.seek(0x120 + data_block_header_index * 0x10)
        cylinder_index = disk_image.read(0x1)[0]
        if cylinder_index == 0xff:
            continue
        head_index = disk_image.read(0x1)[0]
        sector_index = disk_image.read(0x1)[0]
        sector_size_this_block = 0x80 << disk_image.read(0x1)[0]
        
        if sector_size is None:
            sector_size = sector_size_this_block
        else:
            if sector_size_this_block != sector_size:
                raise Exception("Sector size mismatch!")
        
        start_addr = header_size + data_block_index*sector_size
        
        sector_list.append( { 'cylinder': cylinder_index, 'head': head_index, 'sector': sector_index, 'size': sector_size, 'start_addr': start_addr } )
    
        data_block_index += 1
        
    return sector_list


def load_translations_csv(filename):
    trans = {}
    with open(filename, 'r', encoding='utf8', newline='') as csv_in:
        for row in csv.reader(csv_in, quoting=csv.QUOTE_ALL):
            if row[0] == "*":
                continue

            data = { 'original': row[1] }
            if len(row) > 2:
                data['translation'] = row[2]
            trans[row[0]] = data
    return trans

    
def load_notes_csv(filename):
    with open(filename, 'r', encoding='utf8', newline='') as csv_in:
        for row in csv.reader(csv_in, quoting=csv.QUOTE_ALL):
            if row[0] == "*":
                return row[1]
    return None


EVENT_CODE_INFO = {
    0x00: { 'length': 1, 'terminator': True }, # Terminator
    0x01: { 'length': 1 }, # Newline
    0x02: { 'length': 1 },
    0x03: { 'length': 1 }, # Wait for keypress
    0x04: { 'length': 1 },
    0x05: { 'length': 1 }, # Page break
    0x06: { 'length': 1, 'terminator': True }, # Unknown terminator
    0x07: { 'length': 1, 'terminator': True }, # Return
    0x08: { 'length': 1 },
    0x09: { 'length': 2 }, # Party member's name
    0x0a: { 'length': 1, 'terminator': True }, # Not sure on this... seems weird
    0x0b: { 'length': 1 },
    0x0c: { 'length': 3 },
    0x0d: { 'length': 1, 'terminator': True },
    0x0e: { 'length': 1 },
    0x0f: { 'length': 3 }, # Jump
    0x10: { 'length': 3 }, # Subroutine call
    0x11: { 'length': 3 }, # Something about conditions...
    0x12: { 'length': 3 }, # ...
    0x13: { 'length': 3 }, # ...
    0x14: { 'length': 3 }, # ...
    0x15: { 'length': 3 }, # Assembly call
    0x16: { 'length': 11 }, # Multiple calls? Based on leader?
    
    0x1a: { 'length': 1 },
    0x1c: { 'length': 1 },
    0x1e: { 'length': 1 },
    0x1f: { 'length': 1 },
    
}
    
def disassemble_event(scenario_data, base_addr, start_addr, continuation_extent_end_addr=None):
    addr = start_addr - base_addr
    instructions = []
    
    jumps = set()

    while True:
        if addr+base_addr in jumps:
            jumps.remove(addr+base_addr)

            # Split up text if a jump lands in the middle of a block of text.
            if len(instructions) > 0 and 'text' in instructions[-1]:
                instructions.append( { 'addr': addr+base_addr, 'text': "" } )
        
        if scenario_data[addr] < 0x20:
            code = scenario_data[addr]
            
            if code not in EVENT_CODE_INFO:
                raise Exception(f"Unknown code {scenario_data[addr]:02x} at {addr+base_addr:03x}!")
            
            code_info = EVENT_CODE_INFO[code]
            
            instructions.append( { 'addr': addr+base_addr, 'code': code, 'data': scenario_data[addr+1:addr+1+code_info['length'] - 1], 'length': code_info['length'] } )
            
            addr += code_info['length']
            
            if code == 0x0f:
                jumps.add(int.from_bytes(instructions[-1]['data'], byteorder='little'))
            elif code == 0x15: # ASM call
                if int.from_bytes(instructions[-1]['data'], byteorder='little') == 0xe887:
                    break
            elif 'terminator' in code_info:
                if addr+base_addr in jumps and continuation_extent_end_addr is not None and addr+base_addr <= continuation_extent_end_addr:
                    raise Exception(f"Event at {start_addr:04x} has both a jump to the end and a continuation. So confusing...")
                elif addr+base_addr in jumps:
                    jumps.remove(addr+base_addr)
                elif continuation_extent_end_addr is not None and addr+base_addr <= continuation_extent_end_addr:
                    instructions[-1]['continue'] = True
                else:
                    break
        else:
            if len(instructions) == 0 or 'text' not in instructions[-1]:
                instructions.append( { 'addr': addr+base_addr, 'text': "" } )
        
            try:        
                if scenario_data[addr] >= 0xe0: # Kanji block above 0xe0 is two bytes each.
                    instructions[-1]['text'] += scenario_data[addr:addr+2].decode('shift-jis')
                    addr += 2
                elif scenario_data[addr] >= 0xa0: # Half-width katakana are between 0xa0 and 0xdf. One byte each.
                    instructions[-1]['text'] += scenario_data[addr:addr+1].decode('shift-jis')
                    addr += 1
                elif scenario_data[addr] >= 0x80:
                    instructions[-1]['text'] += scenario_data[addr:addr+2].decode('shift-jis')
                    addr += 2
                elif scenario_data[addr] >= 0x20:
                    instructions[-1]['text'] += scenario_data[addr:addr+1].decode('shift-jis')
                    addr += 1
            except UnicodeDecodeError as e:
                print(f"Unable to interpret SJIS sequence {scenario_data[addr:addr+2].hex()} at {addr+base_addr:04x} while disassembling event at {start_addr:04x}")
                raise e
                
    return instructions


def encode_event(text, max_length = None):
    encoded = bytearray()
    references = []
    locators = {}
    
    terminated = False

    text = text.replace("\r", "")
    
    while len(text) > 0:
    
        terminated = False
        
        if text.startswith("\n<CONT>"):
            current_encoded_bytes = b''
            text = text[7:]
            continue
            
        current_encoded_bytes = None
    
        if text.startswith("<X"):
            hex_bytes = ""
            text = text[2:]
            while text[0] != ">":
                hex_bytes += text[0]
                text = text[1:]
            text = text[1:]
            
            current_encoded_bytes = bytes.fromhex(hex_bytes)
            if current_encoded_bytes[0] == 0x06 or current_encoded_bytes[0] == 0x0a or current_encoded_bytes[0] == 0x0d:
                terminated = True
            
        elif text.startswith("<JUMP"):
            call_addr = int(text[5:9], base=16)
            text = text[10:]
            references.append((len(encoded) + 1, call_addr))
            current_encoded_bytes = b'\x0f' + int.to_bytes(call_addr, length=2, byteorder='little')
            
            if len(text) == 0:
                terminated = True
        
        elif text.startswith("<CALL"):
            call_addr = int(text[5:9], base=16)
            text = text[10:]
            references.append((len(encoded) + 1, call_addr))
            current_encoded_bytes = b'\x10' + int.to_bytes(call_addr, length=2, byteorder='little')
            
        elif text.startswith("<ASM"):
            text = text[4:]
            if text.startswith("_NORET"):
                text = text[6:]
                terminated = True
            asm_addr = int(text[:4], base=16)
            text = text[5:]
            current_encoded_bytes = b'\x15' + int.to_bytes(asm_addr, length=2, byteorder='little')
            
        elif text.startswith("<LEADER"):
            text = text[7:]
            current_encoded_bytes = b'\x16'
            for ref_index in range(5):
                call_addr = int(text[0:4], base=16)
                references.append((len(encoded) + ref_index*2 + 1, call_addr))
                current_encoded_bytes += int.to_bytes(call_addr, 2, 'little')
                text = text[5:]
                
        elif text.startswith("<IF_NOT"):
            flag = int(text[7:11], base=16)
            text = text[12:]
            current_encoded_bytes = b'\x11' + int.to_bytes(flag, length=2, byteorder='little')
            
        elif text.startswith("<IF"):
            flag = int(text[3:7], base=16)
            text = text[8:]
            current_encoded_bytes = b'\x12' + int.to_bytes(flag, length=2, byteorder='little')
        
        elif text.startswith("<CLEAR"):
            flag = int(text[6:10], base=16)
            text = text[11:]
            current_encoded_bytes = b'\x13' + int.to_bytes(flag, length=2, byteorder='little')
            
        elif text.startswith("<SET"):
            flag = int(text[4:8], base=16)
            text = text[9:]
            current_encoded_bytes = b'\x14' + int.to_bytes(flag, length=2, byteorder='little')
            
        elif text.startswith("<RET_IL>"):
            text = text[8:]
            current_encoded_bytes = b'\x06'
            terminated = True
            
        elif text.startswith("<RETN>"):
            text = text[6:]
            current_encoded_bytes = b'\x07'
            terminated = True
            
        elif text.startswith("<CH"):
            current_encoded_bytes = b'\x09' + int.to_bytes(int(text[3:4]), length=1, byteorder='little')
            text = text[5:]
            
        elif text.startswith("<LOC"):
            loc_addr = int(text[4:8], base=16)
            loc_offset = len(encoded)
            locators[loc_addr] = loc_offset
            current_encoded_bytes = b''
            text = text[9:]
            
        elif text.startswith("<N>\n"):
            current_encoded_bytes = b'\x01'
            text = text[4:]
            
        elif text.startswith("<WAIT>\n"):
            current_encoded_bytes = b'\x03'
            text = text[7:]

        elif text.startswith("<PAGE>\n"):
            current_encoded_bytes = b'\x05'
            text = text[7:]
            
        elif text.startswith("<END>\n"):
            current_encoded_bytes = b'\x00'
            text = text[6:]
            
        elif text.startswith("<"):
            raise Exception("Unknown tag " + text[:10] + "!")
            
        
        elif text.startswith("\n\n"):
            current_encoded_bytes = b'\x05'
            text = text[2:]
        elif text.startswith("\n"):
            current_encoded_bytes = b'\x01'
            text = text[1:]
        else:
            current_encoded_bytes = text[0].encode(encoding='shift-jis')
            text = text[1:]
        
        if not terminated and max_length is not None and len(encoded) + len(current_encoded_bytes) > max_length - 1:
            print("Text is too long! Truncating.")
            break
        elif terminated and max_length is not None and len(encoded) + len(current_encoded_bytes) > max_length:
            raise Exception("Terminated text is too long!")
        else:
            encoded += current_encoded_bytes
            
    if not terminated:
        encoded += b'\x00'
    
    return encoded, references, locators


class CodeHook:
    def should_handle(self, instruction):
        raise NotImplementedError("Handle this in a subclass")

    def get_next_ip(self, instruction):
        if instruction.id == X86_INS_JMP or instruction.id == X86_INS_LJMP or X86_GRP_RET in instruction.groups:
            return None
        else:
            return instruction.address + instruction.size

    def generate_links(self, instruction, block_pool, current_block, registers):
        pass


class EmptyHook(CodeHook):
    def __init__(self, addr, is_call, next_ip=None):
        self._addr = addr
        self._is_call = is_call
        self._next_ip = next_ip

    def get_next_ip(self, instruction):
        if self._next_ip is None:
            return super().get_next_ip(instruction)
        else:
            return self._next_ip

    def should_handle(self, instruction):
        if self._is_call:
            return (X86_GRP_CALL in instruction.groups or X86_GRP_JUMP in instruction.groups) and instruction.operands[0].type == CS_OP_IMM and instruction.operands[0].imm == self._addr
        else:
            return instruction.address == self._addr

    def generate_links(self, instruction, block_pool, current_block, registers):
        pass


class HardcodedValueHook(CodeHook):
    def __init__(self, addr):
        self._addr = addr
        
    def should_handle(self, instruction):
        return self._addr == instruction.address
        
    def generate_links(self, instruction, block_pool, current_block, registers):
        if not instruction.id == X86_INS_MOV or not instruction.operands[0].type == CS_OP_REG or not instruction.operands[0].reg == X86_REG_SI or not instruction.operands[1].type == CS_OP_IMM:
            raise Exception(f"Invalid instruction at hardcoded hook address! {instruction.mnemonic} {instruction.op_str}")
        
        addr = instruction.operands[1].imm
        link = Link(instruction.address + 1, addr)
        link.connect_blocks(current_block, block_pool.get_block(addr, EventBlock))

        
class CallWithoutReturnCodeHook(CodeHook):
    def __init__(self, addr):
        self._addr = addr

    def should_handle(self, instruction):
        return X86_GRP_CALL in instruction.groups and instruction.operands[0].type == CS_OP_IMM and instruction.operands[0].imm == self._addr

    def get_next_ip(self, instruction):
        return None

    def generate_links(self, instruction, block_pool, current_block, registers):
        link = Link(instruction.address + 1, self._addr, source_instruction_addr=instruction.address, execution_context=registers.copy())

        if (self._addr < current_block.base_addr or self._addr >= current_block.base_addr + len(block_pool.data)):
            link.connect_blocks(current_block, None)
        else:
            target_block = block_pool.get_block(self._addr, CodeBlock)
            link.connect_blocks(current_block, target_block)


class WorldMapTableCodeHook(CodeHook):

    def should_handle(self, instruction):
        return instruction.address == 0xe27e

    def get_next_ip(self, instruction):
        return 0xe29c

    def generate_links(self, instruction, block_pool, current_block, registers):
        if X86_REG_SI in registers and X86_REG_CX in registers:
            table_address = registers[X86_REG_SI]['value'] # X86_REG_SI
            table_size = registers[X86_REG_CX]['value'] # X86_REG_CX
        
            table_address -= 0xe000
            for _ in range(table_size):
                jump_address = int.from_bytes(block_pool.data[table_address+0x8:table_address+0xa], byteorder='little')
                event_address = int.from_bytes(block_pool.data[table_address+0xa:table_address+0xc], byteorder='little')

                jump_link = Link(table_address + 0x8 + 0xe000, jump_address)
                event_link = Link(table_address + 0xa + 0xe000, event_address)

                jump_link.connect_blocks(current_block, block_pool.get_block(jump_address, CodeBlock))
                event_link.connect_blocks(current_block, block_pool.get_block(event_address, EventBlock))

                table_address += 0xc
        else:
            raise Exception("Don't know where the overworld name table is!")


class StandardEventCodeHook(CodeHook):
    def should_handle(self, instruction):
        if (X86_GRP_CALL in instruction.groups or X86_GRP_JUMP in instruction.groups) and instruction.operands[0].type == CS_OP_IMM:
            return instruction.operands[0].value.imm in [ 0x6e77, 0x6e7c, 0x70eb, 0x84be, 0x853f, 0x8559, 0x99ba, 0x99cc ]

    def generate_links(self, instruction, block_pool, current_block, registers):
        if X86_REG_SI in registers:
            event_addr = registers[X86_REG_SI]['value']

            if event_addr >= current_block.base_addr and event_addr < current_block.base_addr + len(block_pool.data):

                disassembly = disassemble_event(block_pool.data, current_block.base_addr, registers[X86_REG_SI]['value'])
        
                if 'source_addr' in registers[X86_REG_SI]:

                    event_link = Link(registers[X86_REG_SI]['source_addr'], registers[X86_REG_SI]['value'])
                    event_link.connect_blocks(current_block, block_pool.get_block(registers[X86_REG_SI]['value'], EventBlock))
            
                    registers[X86_REG_SI]['continue_from_addr'] = registers[X86_REG_SI]['value']
                    registers[X86_REG_SI]['value'] = disassembly[-1]['addr'] + disassembly[-1]['length']
            
                    del registers[X86_REG_SI]['source_addr']
                else:
                    current_block = block_pool.get_block(registers[X86_REG_SI]['continue_from_addr'], EventBlock)
                    current_block.set_continuation_extent(registers[X86_REG_SI]['value'])
            else:
                print(f"TODO: Log global event at {event_addr:04x}?")
        
        else:
            print(registers)
            raise Exception(f"No known event address for event call at {instruction.address:04x}")


class PointerTableHook(CodeHook):
    def __init__(self, block_type, is_call, addr, length, stride, pointer_offset, table_addr=None, address_register=None, next_ip=None):
        self._block_type = block_type
        self._is_call = is_call
        self._addr = addr
        self._length = length
        self._stride = stride
        self._pointer_offset = pointer_offset
        self._table_addr = table_addr
        self._address_register = address_register
        self._next_ip = next_ip

    def should_handle(self, instruction):
        if self._is_call:
            return (X86_GRP_CALL in instruction.groups or X86_GRP_JUMP in instruction.groups) \
                and instruction.operands[0].type == CS_OP_IMM and \
                instruction.operands[0].value.imm == self._addr
        else:
            return instruction.address == self._addr
            
    def get_next_ip(self, instruction):
        if self._is_call:
            return super().get_next_ip(instruction)
        else:
            return self._next_ip
        
    def generate_links(self, instruction, block_pool, current_block, registers):
        if self._address_register is not None:
            table_addr = registers[self._address_register]['value']
        else:
            table_addr = self._table_addr
        
    
        for table_entry_index in range(self._length):
            table_entry_addr = table_addr + table_entry_index*self._stride + self._pointer_offset
            event_addr = int.from_bytes(block_pool.data[table_entry_addr - 0xe000:table_entry_addr + 2 - 0xe000], byteorder='little')
            if event_addr >= current_block.base_addr and event_addr < current_block.base_addr + len(block_pool.data):
                event_link = Link(table_entry_addr, event_addr)
                event_link.connect_blocks(current_block, block_pool.get_block(event_addr, self._block_type))

                
class NpcTable6d38CodeHook(CodeHook):
    def should_handle(self, instruction):
        if (X86_GRP_CALL in instruction.groups or X86_GRP_JUMP in instruction.groups) and instruction.operands[0].type == CS_OP_IMM:
            return instruction.operands[0].value.imm in [ 0x6d32, 0x6d38 ]

    def generate_links(self, instruction, block_pool, current_block, registers):
        if X86_REG_SI in registers:
            table_destination = registers[X86_REG_SI]['value']
            table_destination -= 0xe000

            while block_pool.data[table_destination] != 0xff:
                jump_addr_offset = 3 if block_pool.data[table_destination] & 0x40 == 0 else 5
                table_entry = int.from_bytes(block_pool.data[table_destination + jump_addr_offset:table_destination + jump_addr_offset + 2], byteorder='little')
                #print(f"  Link to {table_entry:04x}")
                link = Link(table_destination + jump_addr_offset + 0xe000, table_entry)
                link.connect_blocks(current_block, block_pool.get_block(table_entry, CodeBlock))
                table_destination += jump_addr_offset + 2
        else:
            raise Exception("Don't know what the table address was!!")


class NpcTable6e5cCodeHook(CodeHook):
    def should_handle(self, instruction):
        if (X86_GRP_CALL in instruction.groups or X86_GRP_JUMP in instruction.groups) and instruction.operands[0].type == CS_OP_IMM:
            return instruction.operands[0].value.imm in [ 0x6e5c ]

    def generate_links(self, instruction, block_pool, current_block, registers):
        if X86_REG_DX in registers:
            table_destination = registers[X86_REG_DX]['value']

            table_destination -= 0xe000
            table_size = int.from_bytes(block_pool.data[table_destination:table_destination+2], byteorder='little') - 1
            for table_index in range(table_size):
                table_entry = int.from_bytes(block_pool.data[table_destination + 2 + table_index*2:table_destination + 2 + (table_index + 1)*2], byteorder='little')
                if table_entry >= 0xe000:
                    link = Link(table_destination + 2 + table_index*2 + 0xe000, table_entry)
                    link.connect_blocks(current_block, block_pool.get_block(table_entry, CodeBlock))
        else:
            raise Exception("Don't know what the table address was!!")


class AlternateCombatStartTextCodeHook(CodeHook):
    def should_handle(self, instruction):
        if instruction.id == X86_INS_MOV and len(instruction.operands) > 0 and instruction.operands[0].type == CS_OP_MEM:
            return instruction.operands[0].mem.disp == 0xdd04 or instruction.operands[0].mem.disp == 0xdd04 - 0x10000

    def generate_links(self, instruction, block_pool, current_block, registers):
        if len(instruction.operands) > 1 and instruction.operands[1].type == CS_OP_REG:
            if instruction.operands[1].reg in registers:
                source_addr = registers[instruction.operands[1].reg]['source_addr']
                event_addr = registers[instruction.operands[1].reg]['value']
                if event_addr >= current_block.base_addr and event_addr < current_block.base_addr + len(block_pool.data):
                    link = Link(source_addr, event_addr)
                    link.connect_blocks(current_block, block_pool.get_block(event_addr, EventBlock))
                else:
                    pass
            else:
                raise Exception(f"Combat start text is being written from register {instruction.reg_id(instruction.operands[1].reg)} at {instruction.address:04x}, but that register's value is unknown.")
        else:
            raise Exception(f"Don't know how to interpret alternate combat start text being written at {instruction.address:04x}!")


class Scenario_11_00_24_FakeWorldMapTable(CodeHook):
    def should_handle(self, instruction):
        return instruction.address == 0xe14f
    
    def get_next_ip(self, instruction):
        return 0xe168

    def generate_links(self, instruction, block_pool, current_block, registers):
        table_addr = registers[X86_REG_SI]['value']
        addr = int.from_bytes(block_pool.data[table_addr + 8 - current_block.base_addr:table_addr + 10 - current_block.base_addr], 'little')
        link = Link(table_addr + 8, addr)
        link.connect_blocks(current_block, block_pool.get_block(addr, EventBlock))


class Scenario_13_01_26_JumpTable(CodeHook):
    def should_handle(self, instruction):
        return instruction.address == 0xe0ca

    def generate_links(self, instruction, block_pool, current_block, registers):
        for entry_index in range(7):
            entry_addr = 0xe117 + entry_index*2
            addr = int.from_bytes(block_pool.data[entry_addr-0xe000:entry_addr-0xe000 + 2], 'little')
            link = Link(entry_addr, addr)
            link.connect_blocks(current_block, block_pool.get_block(addr, CodeBlock))

class Scenario_20_00_20_TableCodeHook(CodeHook):
    def should_handle(self, instruction):
        return instruction.address == 0xe200

    def generate_links(self, instruction, block_pool, current_block, registers):
        link = Link(None, 0xe373)
        link.connect_blocks(current_block, block_pool.get_block(link.target_addr, EventBlock))

        link = Link(None, 0xe383)
        link.connect_blocks(current_block, block_pool.get_block(link.target_addr, EventBlock))

class Scenario_20_00_20_WriteNumberCodeHook(CodeHook):
    def should_handle(self, instruction):
        return instruction.address == 0xe154

    def generate_links(self, instruction, block_pool, current_block, registers):
        link = Link(instruction.address + 1, 0xe63b, instruction.address)
        link.connect_blocks(current_block, block_pool.get_block(link.target_addr, EventBlock))


class Link:
    def __init__(self, source_addr, target_addr, source_instruction_addr=None, execution_context={}):
        self._source_addr = source_addr
        self._target_addr = target_addr

        self._source_instruction_addr = source_instruction_addr
        self._execution_context = execution_context

        self._source_block = None
        self._target_block = None

    @property
    def source_addr(self):
        return self._source_addr

    @property
    def source_instruction_addr(self):
        return self._source_instruction_addr

    @property 
    def execution_context(self):
        return self._execution_context

    @property
    def source_block(self):
        return self._source_block

    @property
    def target_addr(self):
        return self._target_addr

    @property
    def target_block(self):
        return self._target_block

    def connect_blocks(self, source_block, target_block):
        self._source_block = source_block
        self._target_block = target_block

        if source_block is not None:
            source_block.connect_outgoing_link(self)
        if target_block is not None:
            target_block.connect_incoming_link(self)

class Block:
    def __init__(self, data, hooks, base_addr, start_addr):
        self._data = data
        self._hooks = hooks
        self._base_addr = base_addr
        self._start_addr = start_addr
        self._length = None
        
        self._incoming_links = []
        self._outgoing_links = []
        self._internal_references = []

        self._incoming_link_path_index = []
        self._link_paths = []

        self._explore()
        
    def __str__(self):
        str = f"<{type(self).__name__} {self._start_addr:04x}"
        
        if self._length is not None:
            str += f"~{self.end_addr:04x}"
            
        str += f", {len(self._incoming_links)} incoming, {len(self._outgoing_links)} outgoing>"
        
        return str
    
    @property
    def base_addr(self):
        return self._base_addr
    
    @property
    def start_addr(self):
        return self._start_addr
        
    @property
    def end_addr(self):
        return None if self._length is None else self._start_addr + self._length - 1
        
    @property
    def length(self):
        return self._length

    @property
    def is_explored(self):
        return self._length is not None

    @property
    def is_linked(self):
        return False not in ['is_linked' in link_path_info for link_path_info in self._link_paths]

    @property
    def is_relocatable(self):
        return False not in [link.source_addr is not None for link in self._incoming_links]
    
    def expand(self, addr):
        if addr >= self._start_addr + self._length:
            self._length = addr - self._entry_addr + 1

    def dump(self):
        raise NotImplementedError("Implement this in a subclass!")

    def _explore(self):
        raise NotImplementedError("Implement this in a subclass!")

    def link(self, block_pool):
        raise NotImplementedError("Implement this in a subclass!")
    
    def _context_is_equivalent(self, c1, c2):
        raise NotImplementedError("Implement this in a subclass!")
    
    def move_start_addr(self, new_addr):
        self._start_addr = new_addr
        self._length = None

        self._explore()
    
    def connect_incoming_link(self, link):

        link_key = (link.target_addr, link.execution_context)
        link_path = None
        for existing_link_index, existing_link in enumerate(self._incoming_links):
            existing_link_path = self._incoming_link_path_index[existing_link_index]
            existing_link_path_info = self._link_paths[existing_link_path]

            if existing_link_path_info['key'] == link_key:
                link_path = existing_link_path
                break

        if link_path is None:
            link_path = len(self._link_paths)
            self._link_paths.append( { 'key': link_key } )

        self._incoming_link_path_index.append(link_path)
        self._incoming_links.append(link)

    def connect_outgoing_link(self, link):
        self._outgoing_links.append(link)
    
    def add_internal_reference(self, source_addr, dest_addr, **kwargs):
        ref = { 'source_addr': source_addr, 'dest_addr': dest_addr }
        
        for key, value in kwargs.items():
            ref[key] = value
            
        self._internal_references.append(ref)
        
    def get_internal_references(self):
        for ref in self._internal_references:
            yield ref
    
    def contains(self, addr):
        if self._length is None:
            return addr == self._start_addr
        else:
            return addr >= self._start_addr and addr <= self.end_addr
        
    def get_incoming_links(self):
        for link in self._incoming_links:
            yield link

    def get_outgoing_links(self):
        for link in self._outgoing_links:
            yield link
    
class CodeBlock(Block):
    def dump(self):
        disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
        disassembler.detail = True
        disasm_iter = disassembler.disasm(self._data[self.start_addr - self.base_addr:], self.start_addr)

        done = False        
        while not done:
            instruction = next(disasm_iter)
            
            if True in [isinstance(in_link, Link) and instruction.address == in_link.target_addr for in_link in self._incoming_links]:
                print("--> ", end='')
            else:
                print("    ", end='')
            
            hook_found = False
            for hook in self._hooks:
                if hook.should_handle(instruction):
                    hook_found = True

                    print(f"{instruction.address:04x}  Hook: {hook}", end='')

                    next_ip = hook.get_next_ip(instruction)
                    if next_ip is None:
                        done = True
                    else:
                        disasm_iter = disassembler.disasm(self._data[next_ip - self._base_addr:], next_ip)

                    break

            if not hook_found:
                print(f"{instruction.address:04x}  {instruction.mnemonic:6} {instruction.op_str:25}", end='')

                if self.end_addr is None or instruction.address + instruction.size > self.end_addr:
                    done = True
            
            if True in [isinstance(out_link, Link) and out_link.source_instruction_addr is not None and instruction.address == out_link.source_instruction_addr for out_link in self._outgoing_links]:
                print("--> ", end='')
            else:
                print("    ", end='')
            
            print()

        if self.end_addr is None:
            print("    (Unexplored)")
            
        print()
    
    def _explore(self):
        disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
        disassembler.detail = True
    
        disasm_iter = disassembler.disasm(self._data[self._start_addr - self._base_addr:], self._start_addr)
        next_ip = None
    
        done = False
        while not done:
            instruction = next(disasm_iter)

            hook_found = False
            for hook in self._hooks:
                if hook.should_handle(instruction):
                    hook_found = True

                    next_ip = hook.get_next_ip(instruction)
                    if next_ip is None:
                        done = True
                        next_ip = instruction.address + instruction.size
                    else:
                        disasm_iter = disassembler.disasm(self._data[next_ip - self._base_addr:], next_ip)

                    break

            if not hook_found:
                next_ip = instruction.address + instruction.size

                if instruction.id == X86_INS_JMP or instruction.id == X86_INS_LJMP:
                    done = True
                elif X86_GRP_RET in instruction.groups:
                    done = True

        self._length = next_ip - self.start_addr


    def link(self, block_pool):
        disassembler = Cs(CS_ARCH_X86, CS_MODE_16)
        disassembler.detail = True

        for link, link_path in zip(self._incoming_links, self._incoming_link_path_index):
            link_path_info = self._link_paths[link_path]
            if 'is_linked' in link_path_info:
                continue
            
            link_target_addr = link.target_addr
    
            disasm_iter = disassembler.disasm(self._data[link_target_addr - self._base_addr:], link_target_addr)
            next_ip = None
    
            registers = link.execution_context.copy()

            done = False
            while not done:
                instruction = next(disasm_iter)
        
                hook_found = False
                for hook in self._hooks:
                    if hook.should_handle(instruction):
                        hook_found = True

                        hook.generate_links(instruction, block_pool, self, registers)

                        next_ip = hook.get_next_ip(instruction)
                        if next_ip is None:
                            done = True
                        else:
                            disasm_iter = disassembler.disasm(self._data[next_ip - self._base_addr:], next_ip)

                        break

                if not hook_found:
                    next_ip = instruction.address + instruction.size
                    
                    (_, written_regs) = instruction.regs_access()
                    for r in written_regs:
                        if r in registers:
                            del registers[r]
        
        
                    if X86_GRP_JUMP in instruction.groups: # X86_GRP_JUMP
                        if instruction.operands[0].type == CS_OP_IMM:
                            destination = instruction.operands[0].value.imm

                            link = Link(instruction.address + 1, destination, source_instruction_addr=instruction.address, execution_context=registers.copy())

                            if (destination < self._base_addr or destination >= self._base_addr + len(self._data)):
                                #print(f"TODO: Maybe log global jump to {destination:04x} from {instruction.address:04x}")
                                link.connect_blocks(self, None)
                            else:
                                link.connect_blocks(self, block_pool.get_block(destination, CodeBlock))
                        else:
                            print(f"Jump to non-immediate address from {instruction.address:04x}!!")
                
                        if instruction.id == X86_INS_JMP or instruction.id == X86_INS_LJMP:
                            break
                    elif instruction.id == X86_INS_LOOP:
                        if instruction.operands[0].type == CS_OP_IMM:
                            destination = instruction.operands[0].value.imm
                            link = Link(instruction.address + 1, destination, source_instruction_addr=instruction.address, execution_context=registers.copy())
                            if (destination < self._base_addr or destination >= self._base_addr + len(self._data)):
                                raise Exception(f"Global loop?? {instruction.addr:04x}")
                            else:
                                link.connect_blocks(self, block_pool.get_block(destination, CodeBlock))
                        else:
                            print(f"Loop to non-immediate address from {instruction.address:04x}!!")
                    elif X86_GRP_CALL in instruction.groups:
                        destination = instruction.operands[0].value.imm

                        link = Link(instruction.address + 1, destination, source_instruction_addr=instruction.address, execution_context=registers.copy())

                        if (destination < self._base_addr or destination >= self._base_addr + len(self._data)):
                            link.connect_blocks(self, None)
                        else:
                            target_block = block_pool.get_block(destination, CodeBlock)
                            link.connect_blocks(self, block_pool.get_block(destination, CodeBlock))
                        
                        # Subroutine calls might do anything, so nuke everything we know about the registers at this point.
                        for r in list(registers.keys()):
                            del registers[r]
            
                    elif X86_GRP_RET in instruction.groups:
                        done = True
            
                    elif instruction.id == X86_INS_MOV and instruction.operands[0].type == CS_OP_REG and instruction.operands[1].type == CS_OP_IMM:
                        reg_id = instruction.operands[0].value.reg
                        value = instruction.operands[1].value.imm
                        registers[reg_id] = { 'source_addr': instruction.address + 1, 'value': value }

            link_path_info['is_linked'] = True

    
class EventBlock(Block):
    def __init__(self, data, hooks, base_addr, start_addr):
        self._continuation_extent_end_addr = None

        super().__init__(data, hooks, base_addr, start_addr)

    def dump(self):
        for instruction in disassemble_event(self._data, self.base_addr, self.start_addr, self._continuation_extent_end_addr):
            if True in [not isinstance(in_link, Link) and instruction['addr'] == in_link['dest_addr'] for in_link in self._incoming_links]:
                print("--> ", end='')
            else:
                print("    ", end='')
            
            print(f"{instruction['addr']:04x}  ", end='')
            
            if 'text' in instruction:
                print(instruction['text'], end='')
            else:
                print(f"{instruction['code']:02x} {instruction['data'].hex()} ", end='')
                
            if True in [not isinstance(out_link, Link) and 'source_addr' in out_link and instruction['addr'] == out_link['source_addr'] for out_link in self._outgoing_links]:
                print("--> ", end='')
            else:
                print("    ", end='')
            
            print()
        print()
    
    
    def _explore(self):
        for instruction in disassemble_event(self._data, self.base_addr, self.start_addr, self._continuation_extent_end_addr):
            pass

        self._length = instruction['addr'] + instruction['length'] - self._start_addr
        
    def link(self, block_pool):
        for link, link_path in zip(self._incoming_links, self._incoming_link_path_index):
            link_path_info = self._link_paths[link_path]
            if 'is_linked' in link_path_info:
                continue

            link_target_addr = link.target_addr
            execution_context = link.execution_context
    
            jump_map = {}
    
            for instruction in disassemble_event(self._data, self.base_addr, self.start_addr, 0):
                if instruction['addr'] in jump_map:
                    self.add_internal_reference(jump_map[instruction['addr']] + 1, instruction['addr'], source_instruction_addr=jump_map[instruction['addr']])
                    del jump_map[instruction['addr']]
    
                if 'code' in instruction:
                    code = instruction['code']
                    if code == 0x0f: # Jump
                        arg = int.from_bytes(instruction['data'], byteorder='little')
                        jump_map[arg] = instruction['addr']
                    elif code == 0x10: # Subroutine
                        arg = int.from_bytes(instruction['data'], byteorder='little')
                        link = Link(instruction['addr'] + 1, arg, source_instruction_addr=instruction['addr'])
                        if (arg < self._base_addr or arg >= self._base_addr + len(self._data)):
                            link.connect_blocks(self, None)
                        else:
                            link.connect_blocks(self, block_pool.get_block(arg, EventBlock))

                    elif code == 0x15: # ASM call
                        arg = int.from_bytes(instruction['data'], byteorder='little')
                        link = Link(instruction['addr'] + 1, arg, source_instruction_addr=instruction['addr'])
                        if (arg < self._base_addr or arg >= self._base_addr + len(self._data)):
                            link.connect_blocks(self, None)
                        else:
                            link.connect_blocks(self, block_pool.get_block(arg, CodeBlock))

                    elif code == 0x16: # Subroutine call based on leader
                        for ref_index in range(5):
                            arg = int.from_bytes(instruction['data'][ref_index*2:ref_index*2+2], 'little')
                            link = Link(instruction['addr'] + ref_index*2 + 1, arg, source_instruction_addr=instruction['addr'])
                            if (arg < self._base_addr or arg >= self._base_addr + len(self._data)):
                                link.connect_blocks(self, None)
                            else:
                                link.connect_blocks(self, block_pool.get_block(arg, EventBlock))
        
            for jump_target, jump_source in jump_map.items():
                link = Link(jump_source + 1, jump_target, source_instruction_addr=jump_source)
                if (jump_target < self._base_addr or arg >= self._base_addr + len(self._data)):
                    link.connect_blocks(self, None)
                else:
                    link.connect_blocks(self, block_pool.get_block(jump_target, EventBlock))

                            
            link_path_info['is_linked'] = True
        
    def format_string(self, scenario_data):
        out = ""
        
        jumps = set()

        external_locators = set()
        for link in self._incoming_links:
            external_locators.add(link.target_addr)

        
        for instruction in disassemble_event(scenario_data, self.base_addr, self.start_addr, self._continuation_extent_end_addr):
            if instruction['addr'] in jumps:
                jumps.remove(instruction['addr'])
                if len(out) > 0:
                    out += f"<LOC{instruction['addr']:04x}>"
            elif instruction['addr'] in external_locators:
                if len(out) > 0:
                    out += f"<LOC{instruction['addr']:04x}>"
        
            if 'text' in instruction:
                out += instruction['text']
            else:
                code = instruction['code']
                
                if code == 0x00:
                    if instruction['addr'] + 1 < self.end_addr:
                        out += "<END>\n"
                elif code == 0x01: # Newline
                    if scenario_data[instruction['addr'] - self.base_addr + 1] == 0x01:
                        out += "<N>\n"
                    else:
                        out += "\n"
                elif code == 0x03: # Wait for keypress (implicit newline)
                    out += "<WAIT>\n"
                elif code == 0x05: # Page break
                    if scenario_data[instruction['addr'] - self.base_addr - 1] == 0x01:
                        out += "<PAGE>\n"
                    else:
                        out += "\n\n"
                elif code == 0x06: # Return inline
                    out += "<RET_IL>"
                elif code == 0x07: # Return with newline
                    out += "<RETN>"
                elif code == 0x09: # Party member name
                    out += f"<CH{instruction['data'][0]}>"
                elif code == 0x0f: # Jump
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    out += f"<JUMP{arg:04x}>"
                    jumps.add(arg)
                elif code == 0x10: # Subroutine
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    out += f"<CALL{arg:04x}>"
                elif code == 0x11: # Conditional, inverted?
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    out += f"<IF_NOT{arg:04x}>"
                elif code == 0x12: # Conditional
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    out += f"<IF{arg:04x}>"
                elif code == 0x13: # Clear flag
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    out += f"<CLEAR{arg:04x}>"
                elif code == 0x14: # Set flag
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    out += f"<SET{arg:04x}>"
                elif code == 0x15: # ASM call
                    arg = int.from_bytes(instruction['data'], byteorder='little')
                    
                    no_return = instruction['addr'] + 3 > self.end_addr
                    
                    out += "<ASM{0}{1:04x}>".format("_NORET" if no_return else "", arg)
                elif code == 0x16: # Call based on party member (includes name)
                    out += "<LEADER"
                    for ref_index in range(5):
                        arg = int.from_bytes(instruction['data'][ref_index*2:ref_index*2+2], 'little')
                        if ref_index > 0:
                            out += ","
                        out += f"{arg:04x}"
                    out += ">"
                else:
                    out += f"<X{code:02x}{instruction['data'].hex()}>"

                if 'continue' in instruction:
                    out += "\n<CONT>"
                
        return out
    
    def set_continuation_extent(self, extent_end_addr):
        if self._continuation_extent_end_addr is None or self._continuation_extent_end_addr < extent_end_addr:
            self._continuation_extent_end_addr = extent_end_addr

            self._length = None
            self._outgoing_links = []

            self._explore()

    def _context_is_equivalent(self, c1, c2):
        c1_continuations = 0 if c1 is None or 'continuations' not in c1 else c1['continuations']
        c2_continuations = 0 if c2 is None or 'continuations' not in c2 else c2['continuations']
        return c1_continuations == c2_continuations


class BlockPool:
    def __init__(self, data, base_addr, hooks):
        self._data = data
        self._base_addr = base_addr
        self._hooks = hooks

        self._blocks = []

    @property
    def data(self):
        return self._data
        
    def get_block(self, addr, block_class):
        for block in self._blocks:
            if block.contains(addr):
                if not isinstance(block, block_class):
                    raise Exception(f"Expected block at address {addr:04x} to be of type {block_class}, but it is of type {type(block)}")
                return block

        new_block = block_class(self._data, self._hooks, self._base_addr, addr)

        for block in self._blocks:
            if new_block.contains(block.start_addr):
                if not isinstance(block, block_class):
                    raise Exception(f"Expected block at address {addr:04x} to be of type {block_class}, but it is of type {type(block)}")
                block.move_start_addr(new_block.start_addr)
                return block

        
        self._blocks.append(new_block)
        return new_block

    def get_blocks(self):
        for block in self._blocks:
            yield block

    def get_unexplored_blocks(self):
        for block in self._blocks:
            if not block.is_explored:
                yield block

    def get_unlinked_blocks(self):
        for block in self._blocks:
            if not block.is_linked:
                yield block
    

def explore(data, base_addr, entry_points, hooks):
    block_pool = BlockPool(data, base_addr, hooks)

    for entry_point in entry_points:
        block = block_pool.get_block(entry_point['target_addr'], EventBlock if 'is_event' in entry_point else CodeBlock)
        
        link = Link(entry_point['source_addr'] if 'source_addr' in entry_point else None, entry_point['target_addr'])
        link.connect_blocks(None, block)


    while True:
        should_continue = False
        
        unlinked_blocks = list(block_pool.get_unlinked_blocks())
        for block in unlinked_blocks:
            block.link(block_pool)
            should_continue = True

        if not should_continue:
            break

    block_list = list(block_pool.get_blocks())
    block_list.sort(key=lambda block: block.start_addr)
    
    return block_list    


def format_sector_key(sector_key):
    return f"{sector_key[0]:02x}.{sector_key[1]:02x}.{sector_key[2]:02x}"
        
def get_scenario_directory(scenario_disk):
    disk_sectors = get_sector_info_nfd0(scenario_disk)
    
    disk_sectors.sort(key=lambda sector_info: (sector_info['cylinder'] << 16) + (sector_info['head'] << 8) + sector_info['sector'])
    
    scenario_directory = {}
    
    sector_index = 256
    while sector_index < 809:
        sector_info = disk_sectors[sector_index]
        
        scenario_key = (sector_info['cylinder'], sector_info['head'], sector_info['sector'])
        scenario_info = { 'sector_length': sector_info['size'], 'sector_addresses' : [ sector_info['start_addr'] ] }
        
        scenario_disk.seek(sector_info['start_addr'])
        scenario_disk.read(6)
        chunk_count = scenario_disk.read(1)[0]
        sector_index += 1
        
        if scenario_key == (0x20, 0x00, 0x20):
            chunk_count = 2
        elif scenario_key == (0x26, 0x01, 0x22):
            chunk_count = 3
        
        if chunk_count > 10:
            raise Exception("Unexpectedly high chunk count in scenario data!")
            

        for _ in range(chunk_count):
            scenario_info['sector_addresses'].append(disk_sectors[sector_index]['start_addr'])
            sector_index += 1

        space_at_end_length = 0
        for sector_addr in scenario_info['sector_addresses'][::-1]:
            scenario_disk.seek(sector_addr)
            sector_data = scenario_disk.read(scenario_info['sector_length'])
            sector_loc = len(sector_data) - 1
            while sector_loc >= 0 and sector_data[sector_loc] == 0:
                sector_loc -= 1
                space_at_end_length += 1
            if sector_loc >= 0:
                break
            
        scenario_info['space_at_end_length'] = space_at_end_length
        
        scenario_directory[scenario_key] = scenario_info
    
    return scenario_directory

def get_combat_directory(scenario_disk):
    disk_sectors = get_sector_info_nfd0(scenario_disk)
    
    disk_sectors.sort(key=lambda sector_info: (sector_info['cylinder'] << 16) + (sector_info['head'] << 8) + sector_info['sector'])
    
    combat_directory = {}
    
    sector_index = 896
    while sector_index < 1006:
        sector_info = disk_sectors[sector_index]
        
        combat_key = (sector_info['cylinder'], sector_info['head'], sector_info['sector'])

        space_at_end_length = 0
        scenario_disk.seek(sector_info['start_addr'])
        sector_data = scenario_disk.read(sector_info['size'])
        sector_loc = len(sector_data) - 1
        while sector_loc >= 0 and sector_data[sector_loc] == 0:
            sector_loc -= 1
            space_at_end_length += 1
        
        combat_directory[combat_key] = { 
            'sector_length': sector_info['size'], 
            'sector_addresses': [ sector_info['start_addr'] ],
            'space_at_end_length': space_at_end_length
        }
        
        sector_index += 1
    
    return combat_directory
    
def extract_scenario_events(scenario_disk, scenario_key, scenario_info):
    scenario_data = b''
    for sector_addr in scenario_info['sector_addresses']:
        scenario_disk.seek(sector_addr)
        scenario_data += scenario_disk.read(scenario_info['sector_length'])
    
    # First step is to find all the asm entry points in the scenario.
    # All scenarios have entry points at e000 and e003. There's also 
    # additional entry point data at e008 in most scenarios, but it
    # varies whether the data there is actual asm code or a list of
    # pointers to code blocks. So there's some elaborate trial-and-error
    # logic to decide how to interpret that information.

    entry_points = [ ]
    entry_points.append( { 'target_addr': 0xe000 } )
    if scenario_key != (0x20, 0x00, 0x20) and scenario_key != (0x26, 0x01, 0x22):
        entry_points.append( { 'target_addr': 0xe003 } )
    
    third_entry_point_offset = 0x8
    
    if scenario_key != (0x20, 0x00, 0x20) and scenario_key != (0x26, 0x01, 0x22):
        possible_entry_point_table = False
        possible_assembly_code = False
        
        # Assembly codes - cmp, xchg, mov, mov, mov, ret, mov, call, jmp, test
        if scenario_data[third_entry_point_offset] in [0x80, 0x94, 0xa0, 0xb8, 0xbe, 0xc3, 0xc6, 0xe8, 0xe9, 0xf6]:
            possible_assembly_code = True
        if (scenario_data[third_entry_point_offset + 1] >= 0xe0 and scenario_data[third_entry_point_offset + 1] <= 0xe0 + (len(scenario_data) >> 8))\
                or scenario_data[third_entry_point_offset + 1] == 0x96:
            possible_entry_point_table = True
            
        
        if not possible_entry_point_table and not possible_assembly_code:
            raise Exception("Don't know what to do with third entry point!!")
        elif possible_entry_point_table and possible_assembly_code:
            if scenario_key in [(0x15, 0x00, 0x27), (0x19, 0x01, 0x23), (0x25, 0x00, 0x23), (0x28, 0x01, 0x27), (0x2a, 0x01, 0x23)]:
                # This is a table, so...
                possible_assembly_code = False
            else:
                raise Exception(f"{format_sector_key(scenario_key)} e008 is ambiguous!!")
        
        if possible_assembly_code:
            entry_points.append( { 'target_addr': third_entry_point_offset + 0xe000 } )
        elif possible_entry_point_table:
            table_addr = third_entry_point_offset
            while True:
                table_entry = int.from_bytes(scenario_data[table_addr:table_addr+2], byteorder='little')
                if table_entry >= 0xe000 and table_entry < 0xe000 + len(scenario_data):
                    # Probably an entry point
                    entry_points.append( { 'target_addr': table_entry, 'source_addr': table_addr } )
                elif table_entry in [0x96c9, 0x96d4, 0x96ea]:
                    # Common entry point outside of scenario data
                    pass
                else:
                    if table_addr == 0x0008:
                        raise Exception("No e008 entry points found for non-overworld scenario {0:06x}".format(scenario_start_addr))
                    break
                table_addr += 2
    
    # Decide what hooks we need to process this scenario during disassembly.
    # All scenarios have a standard set of hooks. Some scenarios have
    # specific hooks for custom behavior.
                
    global_code_hooks = [ 
        StandardEventCodeHook(),
        NpcTable6d38CodeHook(), 
        NpcTable6e5cCodeHook(),
        PointerTableHook(EventBlock, True, 0xa95a, 3, 2, 0, address_register=X86_REG_BX), # Three event pointers, then a pointer to shop contents?
        PointerTableHook(EventBlock, True, 0xa9df, 4, 2, 0, address_register=X86_REG_BX),
    ]
                
    scenario_code_hooks = []
    if scenario_key == (0x10, 0x00, 0x20):
        scenario_code_hooks.append(WorldMapTableCodeHook())
    elif scenario_key == (0x10, 0x01, 0x20):
        scenario_code_hooks.append(PointerTableHook(CodeBlock, False, 0xe019, 63, 4, 2, table_addr=0xe027))
    elif scenario_key == (0x11, 0x00, 0x24):
        scenario_code_hooks.append(Scenario_11_00_24_FakeWorldMapTable())
    elif scenario_key == (0x11, 0x00, 0x25):
        scenario_code_hooks.append(PointerTableHook(EventBlock, False, 0xe03b, 9, 10, 8, table_addr=0xe0b1))
    elif scenario_key == (0x13, 0x01, 0x20):
        scenario_code_hooks.append(Scenario_13_01_26_JumpTable())
    elif scenario_key == (0x18, 0x01, 0x22):
        scenario_code_hooks.append(EmptyHook(0xe2f6, False))
        for hook_addr in [0xe553, 0xe595, 0xe5bc, 0xe5d2, 0xe6aa, 0xe724, 0xe7aa, 0xe7f7, 0xe84a, 0xe856, 0xe886, 0xe8da, 0xe912, 0xe919]:
            scenario_code_hooks.append(HardcodedValueHook(hook_addr))
    elif scenario_key == (0x1b, 0x01, 0x25):
        scenario_code_hooks.append(CallWithoutReturnCodeHook(0xe372))
    elif scenario_key == (0x1c, 0x00, 0x21):
        scenario_code_hooks.append(CallWithoutReturnCodeHook(0xe363))
    elif scenario_key == (0x1c, 0x00, 0x25):
        scenario_code_hooks.append(CallWithoutReturnCodeHook(0xe3eb))
    elif scenario_key == (0x1c, 0x01, 0x21):
        scenario_code_hooks.append(CallWithoutReturnCodeHook(0xe30e))
    elif scenario_key == (0x1d, 0x00, 0x22):
        scenario_code_hooks.append(PointerTableHook(CodeBlock, False, 0xe07c, 6, 2, 0, table_addr=0xe0a4))
    elif scenario_key == (0x1e, 0x01, 0x26):
        scenario_code_hooks.append(PointerTableHook(EventBlock, False, 0xe093, 10, 2, 0, table_addr=0xe0bb, next_ip=0xe09a))
    elif scenario_key == (0x20, 0x00, 0x20):
        scenario_code_hooks.append(EmptyHook(0xe164, False, 0xe166)) # Ignores a couple of increments that would sometimes skip the first character of a string
        scenario_code_hooks.append(Scenario_20_00_20_TableCodeHook())
        scenario_code_hooks.append(Scenario_20_00_20_WriteNumberCodeHook())
    elif scenario_key == (0x24, 0x00, 0x26):
        scenario_code_hooks.append(PointerTableHook(EventBlock, False, 0xe046, 16, 2, 0, table_addr=0xe75d))
    elif scenario_key == (0x30, 0x00, 0x25):
        scenario_code_hooks.append(PointerTableHook(EventBlock, False, 0xe084, 4, 2, 0, table_addr=0xe08d))
    elif scenario_key == (0x30, 0x00, 0x26):
        scenario_code_hooks.append(PointerTableHook(EventBlock, False, 0xe1ee, 4, 2, 0, table_addr=0xe1f7))
    
    # Now, explore the asm code, using the hooks to discover any event blocks it
    # happens to trigger.
    blocks = explore(scenario_data, 0xe000, entry_points, scenario_code_hooks + global_code_hooks)
    
    # Organize and format all the events we found.
    events = {}

    for block in blocks:
        if isinstance(block, EventBlock):
            event_info = { 
                'text': block.format_string(scenario_data), 
                'length': block.length,
                'is_relocatable': block.is_relocatable,
                'references': []
            }

            for link in block.get_incoming_links():
                event_info['references'].append( { 'source_addr': link.source_addr, 'target_addr': link.target_addr, } )
                if link.source_block is not None and isinstance(link.source_block, EventBlock):
                    event_info['references'][-1]['source_event_addr'] = link.source_block.start_addr
            
            for internal_ref in block.get_internal_references():
                event_info['references'].append( { 'source_addr': internal_ref['source_addr'], 'target_addr': internal_ref['dest_addr'], 'source_event_addr': block.start_addr } )

            events[block.start_addr] = event_info

    return events

def extract_combat_events(scenario_disk, combat_key, combat_info):

    combat_data = b''
    for sector_addr in combat_info['sector_addresses']:
        scenario_disk.seek(sector_addr)
        combat_data += scenario_disk.read(combat_info['sector_length'])
    

    global_code_hooks = [ 
        StandardEventCodeHook(),
        AlternateCombatStartTextCodeHook(),
        EmptyHook(0x681b, True),
        EmptyHook(0x684f, True),
        EmptyHook(0x7ff0, True),
        EmptyHook(0x8350, True), # This one looks like it happens to redraw the character status windows
        EmptyHook(0x99fe, True),
    ]

    combat_code_hooks = []
    if combat_key == (0x3c, 0x01, 0x23):
        combat_code_hooks.append(EmptyHook(0xddd2, False, 0xddd7)) # Skip a push/pop pair with a meaningless global call in between
    elif combat_key == (0x3c, 0x01, 0x24):
        combat_code_hooks.append(EmptyHook(0xdd5e, False, 0xdd63)) # Same pattern
    elif combat_key == (0x3e, 0x01, 0x22):
        combat_code_hooks.append(EmptyHook(0xdd56, False, 0xdd65)) # Long push/pop block that doesn't appear to do anything significant
        
    entry_points = []
    for entry_addr in [0xdd0c, 0xdd0f, 0xdd12, 0xdd15]:
        entry_points.append( { 'target_addr': entry_addr } )

    if combat_key == (0x3e, 0x01, 0x24) or combat_key == (0x3e, 0x01, 0x25):
        enemy_count = 1
    elif combat_key == (0x3a, 0x01, 0x22):
        enemy_count = 3
    else:
        enemy_count = 4

    for enemy_index in range(enemy_count):
        name_addr = enemy_index * 0x40 + 0x30
        if combat_data[name_addr] == 0x00:
            break

        entry_points.append( { 'target_addr': name_addr + 0xdc00, 'is_event': True } )

        for enemy_entry_point_index in range(4):
            enemy_entry_point_addr = 0x120 + enemy_index*0x8 + enemy_entry_point_index*0x2
            entry_points.append( { 'target_addr': int.from_bytes(combat_data[enemy_entry_point_addr:enemy_entry_point_addr+2], byteorder='little'), 'source_addr': enemy_entry_point_addr } )
        
        
    entry_points.append( { 'target_addr': int.from_bytes(combat_data[0x104:0x106], byteorder='little'), 'source_addr': 0xdd04, 'is_event': True } )
        
    blocks = explore(combat_data, 0xdc00, entry_points, combat_code_hooks + global_code_hooks)
    
    events = {}

    for block in blocks:
        if isinstance(block, EventBlock):
            event_info = { 
                'text': block.format_string(combat_data), 
                'length': block.length,
                'is_relocatable': block.is_relocatable,
                'references': []
            }

            for link in block.get_incoming_links():
                event_info['references'].append( { 'source_addr': link.source_addr, 'target_addr': link.target_addr, } )
                if link.source_block is not None and isinstance(link.source_block, EventBlock):
                    event_info['references'][-1]['source_event_addr'] = link.source_block.start_addr

            for internal_ref in block.get_internal_references():
                event_info['references'].append( { 'source_addr': internal_ref['source_addr'], 'target_addr': internal_ref['dest_addr'], 'source_event_addr': block.start_addr } )

            events[block.start_addr] = event_info
            
    return events