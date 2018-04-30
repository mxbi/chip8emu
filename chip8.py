import random

class Chip8:
    def __init__(self, rom):
        self.ram = [0x0] * 4096  # 4K ram (12 bit addresses)
        self.V = [0x0] * 16      # 8 bit registers
        self.I = 0x0             # 16 bit GP register
        self.pc = 0x200          # 16 bit program counter

        self.stack = [None] * 16 # Callstack - default None just to better highlight errors
        self.sp = 0x0            # Stack pointer

        self.t_delay = 0x0       # 8 bit delay register
        self.t_sound = 0x0       # 8 bit sound register

        self.display = [0x0] * (64 * 32) # Monochrome display

        self.clock_speed = 512
        self.clock = 0
        self.rtc_mod = self.clock_speed // 60

        self.load_rom(rom)

        self.instructions = {
            0x1000: self.op_1NNN,
            0x2000: self.op_2NNN,
            0x3000: self.op_3XNN,
            0x4000: self.op_4XNN,
            0x5000: self.op_5XY0,
            0x6000: self.op_6XNN,
            0x7000: self.op_7XNN,
            0x8000: self.op_8000,
            0xA000: self.op_ANNN,
            0xB000: self.op_BNNN,
            0xC000: self.op_CXNN,
            0xD000: self.op_DXYN,
        }

    # Emulate overflow and underflow
    def _8bit(self, val):
        return val % 256

    def _16bit(self, val):
        return val % 65536

    def hex_str(self, val):
        return '{:02X}'.format(val)

    # Pretty-print a memory dump for debugging
    def print_mem(self, arr):
        s = ''
        for ptr in range(len(arr)):
            if ptr % 64 == 0:
                s += '0x{:03X}: '.format(ptr)
            s += self.hex_str(self.ram[ptr])
            s += '\n' if ptr % 64 == 63 else ' '
        print(s)

    # Execute a full clock cycle
    def _cycle_clock(self):
        self.clock += 1

        # Read two bytes from memory, little endian
        opcode = self.ram[self.pc] << 8 | self.ram[self.pc + 1]
        print('0x{:04X}'.format(opcode))

        self.instructions[opcode & 0xF000](opcode) # Mask opcode, get associated function, and execute
        self.pc += 2 # Increment program counter to next instruction

        if self.clock % self.rtc_mod == 0:
            if self.t_delay > 0:
                self.t_delay -= 1
            if self.t_sound > 0:
                self.t_sound -= 1

    # Render to the display in text format to a string
    def render_display(self):
        pix = {1: '█', 0: ' '}
        disp = ''
        for i in range(64 * 32):
            disp += pix[self.display[i]]
            if i % 64 == 63:
                disp += '\n'
        return disp

    # Load a rom from a binary file into memory, starting at memory address 0x200 (512)
    # TODO: Check that this actually works, little/big endian error likely here
    def load_rom(self, rom):
        f = open(rom, 'rb')
        ptr = 0x200
        with open(rom, 'rb'):
            while True:
                byte = f.read(1)
                if not byte:
                    break
                self.ram[ptr] = int.from_bytes(byte, 'big')
                ptr += 1

    ##### INSTRUCTION SET #####
    # https://en.wikipedia.org/wiki/CHIP-8#Opcode_table for more details
    def op_1NNN(self, opcode):  # Goto NNN
        self.pc = opcode & 0x0FFF

    def op_2NNN(self, opcode):  # Call subroutine
        self.stack[self.sp] = self.pc # Place current location on the stack so we can go back to it later
        self.pc = opcode & 0x0FFF

    def op_3XNN(self, opcode):  # Skip next instruction if Vx == NN
        Vx = self.V[(opcode & 0x0F00) >> 8]
        if Vx == (opcode & 0x00FF):
            self.pc += 2  # Skip next instruction

    def op_4XNN(self, opcode):  # Skip next instruction if Vx != NN
        Vx = self.V[(opcode & 0x0F00) >> 8]
        if Vx != (opcode & 0x00FF):
            self.pc += 2

    def op_5XY0(self, opcode):  # Skip next instruction if Vx == Vy
        Vx = self.V[(opcode & 0x0F00) >> 8]
        Vy = self.V[(opcode & 0x00F0) >> 4]
        if Vx == Vy:
            self.pc += 2

    def op_6XNN(self, opcode):  # Set Vx to NN
        self.V[(opcode & 0x0F00) >> 8] = (opcode & 0x00FF)

    def op_7XNN(self, opcode):  # Increment Vx by NN
        self.V[(opcode & 0x0F00) >> 8] = self._8bit(self.V[(opcode & 0x0F00) >> 8] + (opcode & 0x00FF))

    # Determine which 8*** opcode to execute by masking off 8XY*
    def op_8000(self, opcode):
        {0x8000: self.op_8XY0, 0x8001: self.op_8XY1, 0x8002: self.op_8XY2, 0x8003: self.op_8XY3, 0x8004: self.op_8XY4, 0x8005: self.op_8XY5}[opcode & 0xF00F](opcode)

    def op_8XY0(self, opcode):  # Set Vx to value of Vy
        self.V[(opcode & 0x0F00) >> 8] = self.V[(opcode & 0x00F0) >> 4]

    def op_8XY1(self, opcode):  # Bitwise OR, Vx=Vx|Vy
        self.V[(opcode & 0x0F00) >> 8] = self.V[(opcode & 0x0F00) >> 8] | self.V[(opcode & 0x00F0) >> 4]

    def op_8XY2(self, opcode):  # Bitwise AND, Vx=Vx&Vy
        self.V[(opcode & 0x00F0) >> 4] = self.V[(opcode & 0x0F00) >> 8] & self.V[(opcode & 0x00F0) >> 4]

    def op_8XY3(self, opcode):  # Bitwise XOR, Vx=Vx&Vy
        self.V[(opcode & 0x00F0) >> 4] = self.V[(opcode & 0x0F00) >> 8] ^ self.V[(opcode & 0x00F0) >> 4]

    def op_8XY4(self, opcode):  # Vx = Vx + Vy, set VF to 1 if overflow
        sum = self.V[(opcode & 0x0F00) >> 8] + self.V[(opcode & 0x00F0) >> 4]
        self.V[0xF] = int(sum > 0xFFFF)
        self.V[(opcode & 0x0F00) >> 8] = self._8bit(sum)

    def op_8XY5(self, opcode):  # Vx = Vy - Vx, set VF to 1 if NO underflow
        sub = self.V[(opcode & 0x0F00) >> 8] + self.V[(opcode & 0x00F0) >> 4]
        self.V[0xF] = int(sub > 0x0000)
        self.V[(opcode & 0x0F00) >> 8] = self._8bit(sum)

    def op_ANNN(self, opcode): self.I = (opcode & 0x0FFF)  # Set I to NNN
    def op_BNNN(self, opcode): self.pc = self.V[0] + (opcode & 0x0FFF) # Not really sure what this is for
    def op_CXNN(self, opcode): self.V[(opcode & 0x0F00) >> 8] = random.randint(0, 255) & (opcode & 0x00FF) # Random number and mask with NN

    # Draw a sprite starting at (X, Y) with width 8 and height N, using bits starting from address I.
    def op_DXYN(self, opcode):
        x0 = opcode & 0x0F00
        y0 = opcode & 0x00F0
        h = opcode & 0x000F
        ptr = self.I
        for y_offset in range(h):
            row = [int(i) for i in '{0:08b}'.format(self.ram[ptr])] # Get 8 bits as separate integers
            y = y0 + y_offset
            self.display[y * 64 + x0:y + 64 + x0 + 8] = row
            ptr += 1


cpu = Chip8('pong.rom')
cpu.print_mem(cpu.ram)
while True:
    cpu._cycle_clock()
