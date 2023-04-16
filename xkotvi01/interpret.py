import xml.etree.ElementTree as ET
import sys
from collections import OrderedDict
from enum import Enum
import argparse

#This list includes all opcodes
opcodes = [ 'MOVE', 'CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'DEFVAR', 'CALL', 'RETURN',
            'PUSHS', 'POPS', 'ADD', 'SUB', 'MUL', 'IDIV', 'LT', 'GT', 'EQ', 'AND', 'OR', 'NOT',
            'INT2CHAR', 'STRI2INT', 'READ', 'WRITE', 'CONCAT', 'STRLEN', 'GETCHAR', 'SETCHAR', 'TYPE',
            'LABEL', 'JUMP', 'JUMPIFEQ', 'JUMPIFNEQ', 'EXIT', 'DPRINT', 'BREAK' ]   

#This class provides comfortable interface for getting information about program's instructions and their arguments
#It also contains checker of XML validity
class Program:
    def __init__(self, source):
        try:
            self.prog = ET.parse(source)
        except ET.ParseError:
            try:
                self.prog = ET.fromstring(sys.stdin.read())
            except:
                sys.exit(31)
        self.prog = self.prog.getroot()
        if not self.check_xml():
            sys.exit(32)
        self.make_instructions_list()

    #This function includes XML semantic checks
    def check_xml(self):
        if self.prog.tag != 'program':
            return False

        #Checking 'program' tag and it's attributes
        prog_tag_attribs = self.prog.attrib
        for attrib in prog_tag_attribs:
            if attrib != 'name' and attrib != 'description' and attrib != 'language':
                return False
            if attrib == 'language' and self.prog.get(attrib) != 'IPPcode23':
                return False
        
        #Checking instructions and their orders
        orders = []
        instructions = self.prog.findall('*')
        for instr in instructions:
            if instr.tag != 'instruction':
                return False
            instr_attribs = instr.attrib
            is_opcode = False
            is_order = False
            for attrib in instr_attribs:
                value = instr.get(attrib)
                if attrib == 'order':
                    is_order = True
                    if int(value) < 0 or value in orders:
                        return False
                    orders.append(value)
                elif attrib == 'opcode':
                    is_opcode = True
                    if value.upper() not in opcodes:
                        return False
                else:
                    return False
            if not is_opcode or not is_order:
                return False
            
        #Now we can be sure we have XML code that describes a IPPcode23 code
        #and all instructions have all necessary attributes with correct values
        #It is necessary to add that we do not contol the count and semantic of instructions' arguments.
        #We suppose, that if the opcode and order are correct, the whole instruction is correct,
        #because it is a type of error that must be eliminated in parse.php
        return True

    #This fumction reads all instructions form an XML tree and creates a dictionary from them.
    #It also creates the list of orders which can be used for easy moving on dictionary
    #It also creates a dictionary for labels
    def make_instructions_list(self):
        self.orders = []
        self.instructions = {}
        self.labels = {}
        instructions = self.prog.findall('*')
        for instr in instructions:
            order = int(instr.get('order'))
            opcode = instr.get('opcode')
            self.instructions[order] = instr
            if opcode.upper() == 'LABEL':
                label = " ".join(instr.find('arg1').text.strip().split())
                if label in self.labels:
                    sys.exit(52)
                self.labels[label] = order
        self.orders = sorted(self.instructions.keys())
        self.instructions = OrderedDict(sorted(self.instructions.items()))
    
    #This functions returns the opcode of an instruction with defined order
    def get_instruction(self, order):
        inst = self.instructions[order]
        opcode = inst.attrib['opcode']
        return opcode

    #This help function returns the defined XML element of argument of inctruction with defined order 
    def get_argument(self, order, attrib_num):
        instr = self.instructions[order]
        argStr = 'arg' + str(attrib_num)
        arg = instr.find(argStr)
        return arg
    
    #This function returns the type of defined argument of instruction with defined order
    def get_argument_type(self, order, attrib_num):
        arg = self.get_argument(order, attrib_num)
        type = arg.attrib['type']
        return type

    #This function returns the value of defined argument of instruction with defined order
    def get_argument_value(self, order, attrib_num):
        arg = self.get_argument(order, attrib_num)
        value = " ".join(arg.text.strip().split())
        return value

#This class makes work with variables values much easier.
#It stores type and value and provides methods to change it
class Value:
    class Types(Enum):
        INT = 1
        STRING = 2
        BOOL = 3
        NIL = 4

    def __init__(self):
        self.type = None
        self.value = None

    def set_value(self, new_type, new_value):
        self.type = new_type
        self.value = new_value

    def get_type(self):
        return self.type

    def get_value(self):
        return self.value

#This class lets to group variable by frames and provides methods for adding new varibale and reading existing ones
class Frame:
    def __init__(self):
        self.vars = {}
    
    def add_var(self, name, value):
        self.vars[name] = value
    
    def get_var_type(self, name):
        return self.vars[name].get_type()
    
    def get_var_value(self, name):
        return self.vars[name].get_value()
    
    def check_var(self, name):
        if name not in self.vars:
            return False
        return True
            
#This class has algorithms for all instructions processing, attributes for frames, stacks and statistics and simple interface for starting the processing
class Interpret:
    def __init__(self, program, input):
        self.program = program
        self.global_frame = Frame()
        self.local_frames = []
        self.temp_frame = None
        self.call_stack = []
        self.heap = []
        self.processed_instructions = 0
        self.order = None
        self.order_index = None
        if input == sys.stdin:
            self.input = sys.stdin
        else:
            try:
                self.input = open(input, "r")
            except:
                sys.exit(11)


    #This function returns the frame needed variable may be in
    def define_frame(self, var_name):
        frame_code = var_name[0:2].upper()
        if frame_code == 'GF':
            return self.global_frame
        if frame_code == 'LF':
            try:
                frame = self.local_frames[-1]
            except IndexError:
                sys.exit(55)
            return frame
        if frame_code == 'TF':
            if self.temp_frame == None:
                sys.exit(55)
            return self.temp_frame
    
    #This function checks if a var with that name is defined
    def check_var_defined(self, var_name):
        frame = self.define_frame(var_name)
        if frame.check_var(var_name[3:]) == True:
            return True
        return False
        

    #This function checks if a var has value
    def check_var_init(self, var_name):
        frame = self.define_frame(var_name)
        type = frame.get_var_type(var_name[3:])
        if type == None:
            return False
        return True
    
    #This function returns value of a var with defined name
    def get_var_value(self, var_name):
        frame = self.define_frame(var_name)
        return frame.get_var_value(var_name[3:])
    
    #This function returns type of a var with defined name
    def get_var_type(self, var_name):
        frame = self.define_frame(var_name)
        return frame.get_var_type(var_name[3:])
    
    #This function sets value of a var with defined name
    def set_var_value(self, var_name, value):
        frame = self.define_frame(var_name)
        frame.add_var(var_name[3:], value)

    #This function parses the string and convert it into Python format
    def parse_string(self, string):
        decoded_chars = []
        i = 0
        while i < len(string):
            c = string[i]
            if c == "\\":
                decimal_code = int(string[i+1:i+4])
                if decimal_code in [ord("#"), ord("\\"), ord(" ")] or 0 <= decimal_code <= 32:
                    decoded_chars.append(chr(decimal_code))
                    i += 4
                else:
                    decoded_chars.append("\\" + string[i+1:i+4])
                    i += 5
            else:
                decoded_chars.append(c)
                i += 1
        return "".join(decoded_chars)

    #This function analyse the literal type and convert it into Python value
    def get_value_from_literal(self, type, arg):
        value = Value()
        if type == 'int':
            value.type = Value.Types.INT
            value.value = int(arg)
        elif type == 'bool':
            value.type = Value.Types.BOOL
            if arg == 'true':
                value.value = True
            else:
                value.value = False
        elif type == 'nil':
            value.type = Value.Types.NIL
            value.value = None
        elif type == 'string':
            value.type = Value.Types.STRING
            value.value = self.parse_string(arg)
        return value
    
    #This function checks if the label is in program
    def check_label(self, label):
        if label in self.program.labels:
            return True
        else:
            return False
    
    #This help function analyse a symbol, check its definition and initialization and returns it's value
    def get_symb_value(self, type, val):
        if type == 'var':
            if not self.check_var_defined(val):
                sys.exit(54)
            if not self.check_var_init(val):
                sys.exit(56)
            value = Value()
            value.type = self.get_var_type(val)
            value.value = self.get_var_value(val)
        else:
            value = self.get_value_from_literal(type, val)
        return value
    

    #This help function realize checks of types and var existances for math instructions and returns two values
    def math(self):
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)

        value1 = self.get_symb_value(type1, symb1)
        value2 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.INT or value2.type != Value.Types.INT:
            sys.exit(53)

        return var, value1, value2
    
    #This help function realize all checks for relative instruction and returns two values, which can be easily compared
    def relative(self):
        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)
    
        value1 = self.get_symb_value(type1, symb1)
        value2 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.NIL and value2.type != Value.Types.NIL:
            if value1.type != value2.type:
                sys.exit(53)
        if value1.type == Value.Types.NIL and value2.type == Value.Types.NIL:
            sys.exit(53)
        
        #The main idea of that two if is following:
        #Python specification says that any string * 0 is an emplty string
        #Any bool value * 0 is false
        #And math rules say that any integer * 0 is 0
        #So in case of NIL value, we turn it's type on the second operator's type, and set the value to fact zero by multiplying second's value by 0
        #In the end we have two operands with the same type, and one of them still represents NIL value (false, '' or 0)
        #So we can easily compare that values
        if value1.type == Value.Types.NIL:
            value1.type == value2.type
            value1.value = value2.value * 0
        if value2.type == Value.Types.NIL:
            value2.type == value1.type
            value2.value = value1.value * 0
        
        return value1, value2
    
    #This help function realize all checks for logic instructions and returns two real bool values
    def logic(self):
        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)

        value1 = self.get_symb_value(type1, symb1)
        value2 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.BOOL or value2.type != Value.Types.BOOL:
            sys.exit(53)
        
        return value1.value, value2.value
    
    #This function will process all instruction from the first one
    def process_program(self):
        self.order_index = 0
        while True:
            if self.order_index >= len(self.program.orders):
                break
            self.order = self.program.orders[self.order_index]
            opcode = self.program.get_instruction(self.order).upper()
            eval("self." + opcode + "()")
            self.processed_instructions += 1

    #Each instruction has it's own function and processing algorithm

    def MOVE(self): #<var> <symb>
        arg1 = self.program.get_argument_value(self.order, 1)
        if self.check_var_defined(arg1) == False:
            sys.exit(54)
        arg2 = self.program.get_argument_value(self.order, 2)
        arg_type = self.program.get_argument_type(self.order, 2)
        if arg_type == 'var':
            if self.check_var_defined(arg2) == False:
                sys.exit(54)
            if self.check_var_init(arg2) == False:
                sys.exit(56)
            self.set_var_value(arg1, self.get_var_value(arg2))
        else:
            value = self.get_value_from_literal(arg_type, arg2)
            self.set_var_value(arg1, value)

        self.order_index += 1
    
    def CREATEFRAME(self):
        self.temp_frame = Frame()
        self.order_index += 1
    
    def PUSHFRAME(self):
        if self.temp_frame == None:
            sys.exit(55)
        self.local_frames.append(self.temp_frame)
        self.temp_frame = None
        self.order_index += 1
    
    def POPFRAME(self):
        if len(self.local_frames) == 0:
            sys.exit(55)
        self.temp_frame == self.local_frames.pop()
        self.order_index += 1
    
    def DEFVAR(self):   #<var>
        var = self.program.get_argument_value(self.order, 1)
        if self.check_var_defined(var) == True:
            sys.exit(52)
        self.set_var_value(var, Value())
        self.order_index += 1
    
    def CALL(self): #<label>
        label = self.program.get_argument_value(self.order, 1)
        if not self.check_label(label):
            sys.exit(52)
        self.call_stack.append(self.order_index + 1)
        self.order_index = self.program.orders.index(self.program.labels[label])

    def RETURN(self):
        if len(self.call_stack) == 0:
            sys.exit(56)
        ret_index = self.call_stack.pop()
        self.order_index = ret_index
        return
    
    def PUSHS(self):    #<symb>
        symb = self.program.get_argument_value(self.order, 1)
        type = self.program.get_argument_type(self.order, 1)
        value = Value()
        if type == 'var':
            if self.check_var_defined(symb) == False:
                sys.exit(54)
            if self.check_var_init(symb) == False:
                sys.exit(56)
            value.type = self.get_var_type(symb)
            value.value = self.get_var_value(symb)
        else:
            value = self.get_value_from_literal(type, symb)

        self.heap.append(value)
        self.order_index += 1

    def POPS(self): #<var>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        if len(self.heap) == 0:
            sys.exit(56)
        value = self.heap.pop()
        self.set_var_value(var, value)
        self.order_index += 1
        
    def ADD(self):  #<var> <symb1> <symb2>
        var, value1, value2 = self.math()
        newValue = Value()
        newValue.set_value(Value.Types.INT, value1.value + value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1

    def SUB(self):  #<var> <symb1> <symb2>
        var, value1, value2 = self.math()
        newValue = Value()
        newValue.set_value(Value.Types.INT, value1.value - value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1

    def MUL(self):  #<var> <symb1> <symb2>
        var, value1, value2 = self.math()
        newValue = Value()
        newValue.set_value(Value.Types.INT, value1.value * value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1

    def IDIV(self): #<var> <symb1> <symb2>
        var, value1, value2 = self.math()
        if value2.value == 0:
            sys.exit(57)
        newValue = Value()
        newValue.set_value(Value.Types.INT, value1.value // value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1
    
    def LT(self):   #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        value1, value2 = self.relative()
        newValue = Value()
        newValue.set_value(value1.type, value1.value < value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1

    def GT(self):   #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        value1, value2 = self.relative()
        newValue = Value()
        newValue.set_value(value1.type, value1.value > value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1
    
    def EQ(self):   #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        value1, value2 = self.relative()
        newValue = Value()
        newValue.set_value(value1.type, value1.value == value2.value)
        self.set_var_value(var, newValue)
        self.order_index += 1
    
    def AND(self):  #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        
        bool1, bool2 = self.logic()
        value = Value()
        value.set_value(bool, bool1 and bool2)
        self.set_var_value(var, value)
        self.order_index += 1

    def OR(self):  #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        
        bool1, bool2 = self.logic()
        value = Value()
        value.set_value(bool, bool1 or bool2)
        self.set_var_value(var, value)
        self.order_index += 1

    def NOT(self):  #<var> <symb>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        
        symb = self.program.get_argument_value(self.order, 2)
        type = self.program.get_argument_type(self.order, 2)
        value = self.get_symb_value(type, symb)
        if value.type != Value.Types.BOOL:
            sys.exit(53)
        value.set_value(bool, not value.value)
        self.set_var_value(var, value)
        self.order_index += 1

    def INT2CHAR(self): #<var> <symb>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        symb = self.program.get_argument_value(self.order, 2)
        type = self.program.get_argument_type(self.order, 2)

        value = self.get_symb_value(type, symb)
        if value.type != Value.Types.INT:
            sys.exit(53)

        try:
            unicode_char = chr(value.value)
        except ValueError:
            sys.exot(58)

        newValue = Value()
        newValue.set_value(Value.Types.STRING, unicode_char)
        self.set_var_value(var, newValue)
        self.order_index += 1
    
    def STRI2INT(self): #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)

        value1 = self.get_symb_value(type1, symb1)
        value2 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.STRING or value2.type != Value.Types.INT:
            sys.exit(53)
        
        if value2.value >= len(value1.value):
            sys.exit(58)
        
        newValue = Value()
        newValue.type = Value.Types.STRING
        newValue.value = ord(value1.value[value2.value])
        self.set_var_value(var, newValue)
        self.order_index += 1


    def READ(self): #<var> <type>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        needed_type = self.program.get_argument_value(self.order, 2)
        value = Value()
        try:
            if needed_type == 'int':
                inp = int(self.input.readline().rstrip())
                value.type = Value.Types.INT
                value.value = inp
            elif needed_type == 'bool':
                inp = self.input.readline().rstrip()
                if inp == 'true':
                    value.value = True
                else:
                    value.value = False
                value.type = Value.Types.BOOL
            elif needed_type == 'string':
                inp = self.input.readline().rstrip()
                value.type = Value.Types.STRING
                value.value = inp
        except:
            value.type = Value.Types.NIL

        self.set_var_value(var, value)
        self.order_index += 1
    
    def WRITE(self):    #<symb>
        symb = self.program.get_argument_value(self.order, 1)
        type = self.program.get_argument_type(self.order, 1)
        value = self.get_symb_value(type, symb)
        if value.type == Value.Types.INT or value.type == Value.Types.STRING:
            print(value.value, end='')
        elif value.type == Value.Types.NIL:
            print('', end='')
        else:
            if value.value == True:
                print('true', end='')
            else:
                print('false', end='')
        self.order_index += 1
    
    def CONCAT(self):   #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)

        value1 = self.get_symb_value(type1, symb1)
        value2 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.STRING or value2.type != Value.Types.STRING:
            sys.exit(53)
        value = Value()
        value.type = Value.Types.STRING
        value.value = value1.value + value2.value

        self.set_var_value(var, value)
        self.order_index += 1

    def STRLEN(self):   #<var> <symb>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        symb = self.program.get_argument_value(self.order, 2)
        type = self.program.get_argument_type(self.order, 2)
        val = self.get_symb_value(type, symb)

        if val.type != Value.Types.STRING:
            sys.exit(53)
        value = Value()
        value.type = Value.Types.INT
        value.value = len(val.value)
        self.set_var_value(var, value)
        self.order_index += 1

    def GETCHAR(self):  #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)

        value1 = self.get_symb_value(type1, symb1)
        value2 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.STRING or value2.type != Value.Types.INT:
            sys.exit(53)
        if value2.value >= len(value1.value):
            sys.exit(58)

        value = Value()
        value.type = Value.Types.STRING
        value.value = value1.value[value2.value]
        self.set_var_value(var, value)
        self.order_index += 1

    def SETCHAR(self):  #<var> <symb1> <symb2>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)
        if not self.check_var_init(var):
            sys.exit(56)

        var_val = self.program.get_argument_value(self.order, 1)
        var_type = self.program.get_argument_type(self.order, 1)
        symb1 = self.program.get_argument_value(self.order, 2)
        type1 = self.program.get_argument_type(self.order, 2)
        symb2 = self.program.get_argument_value(self.order, 3)
        type2 = self.program.get_argument_type(self.order, 3)

        value1 = self.get_symb_value(var_type, var_val)
        value2 = self.get_symb_value(type1, symb1)
        value3 = self.get_symb_value(type2, symb2)

        if value1.type != Value.Types.STRING or value2.type != Value.Types.INT or value3.type != Value.Types.STRING:
            sys.exit(53)
        if value2.value >= len(value1.value):
            sys.exit(58)

        print(value1.value)
        print(value2.value)
        print(value3.value)
        value = Value()
        value.type = Value.Types.STRING
        value.value = value1.value[:value2.value] + value3.value[0] + value1.value[value2.value + 1:]
        self.set_var_value(var, value)
        self.order_index += 1

    def TYPE(self): #<var> <symb>
        var = self.program.get_argument_value(self.order, 1)
        if not self.check_var_defined(var):
            sys.exit(54)

        symb = self.program.get_argument_value(self.order, 2)
        type = self.program.get_argument_type(self.order, 2)
        val = self.get_symb_value(type, symb)

        value = Value()
        value.type = Value.Types.STRING
        if val.type == Value.Types.INT:
            value.value = 'int'
        elif val.type == Value.Types.STRING:
            value.value = 'string'
        elif val.type == Value.Types.BOOL:
            value.value = 'bool'
        elif val.type == Value.Types.NIL:
            value.value = 'nil'
        else:
            value.value = ''
        
        self.set_var_value(var, value)
        self.order_index += 1

    def LABEL(self):
        self.order_index += 1
        return
    
    def JUMP(self): #<label>
        label = self.program.get_argument_value(self.order, 1)
        if not self.check_label(label):
            sys.exit(52)
        self.order_index = self.program.orders.index(self.program.labels[label])

    def JUMPIFEQ(self): #<label> <symb1> <symb2>
        label = self.program.get_argument_value(self.order, 1)
        if not self.check_label(label):
            sys.exit(52)

        value1, value2 = self.relative()
        if value1.value == value2.value:
            self.order_index = self.program.orders.index(self.program.labels[label])
        else:
            self.order_index += 1

    def JUMPIFNEQ(self):    #<label> <symb1> <symb2>
        label = self.program.get_argument_value(self.order, 1)
        if not self.check_label(label):
            sys.exit(52)

        value1, value2 = self.relative()
        if value1.value != value2.value:
            self.order_index = self.program.orders.index(self.program.labels[label])
        else:
            self.order_index += 1

    def EXIT(self): #<symb>
        type = self.program.get_argument_type(self.order, 1)
        val = self.program.get_argument_value(self.order, 1)
        value = self.get_symb_value(type, val)
        if value.type != Value.Types.INT:
            sys.exit(53)
        if value.value < 0 or value.value > 49:
            sys.exit(57)
        sys.exit(value.value)

    
    def DPRINT(self):   #<symb>
        symb = self.program.get_argument_value(self.order, 1)
        type = self.program.get_argument_type(self.order, 1)
        value = self.get_symb_value(type, symb)
        sys.stderr.write(str(value.value))
        self.order_index += 1

    def BREAK(self):
        sys.stderr.write("###############\n")
        sys.stderr.write("INTERPRET STATE\n")
        sys.stderr.write("\tGLOBAL FRAME:\n")
        for elem in self.global_frame.vars:
            sys.stderr.write(f"\t\tVar name: {elem},\ttype: {self.global_frame.vars[elem].type},\tvalue: {self.global_frame.vars[elem].value}\n")
        sys.stderr.write("\tLOCAL FRAMES:\n")
        lf_count = 0
        for frame in self.local_frames:
            sys.stderr.write(f"\t\tLOCAL FRAME {lf_count + 1}\n")
            for elem in self.local_frames[lf_count].vars:
                sys.stderr.write(f"\t\t\tVar name: {elem},\ttype: {self.local_frames[lf_count].vars[elem].type},\tvalue: {self.local_frames[lf_count].vars[elem].value}\n")
            lf_count += 1
        sys.stderr.write("\tTEMPORARY FRAME:\n")
        if self.temp_frame == None:
            sys.stderr.write("\t\tNOT DEFINED\n")
        else:
            for elem in self.temp_frame.vars:
                sys.stderr.write(f"\t\tVar name: {elem},\ttype: {self.temp_frame.vars[elem].type},\tvalue: {self.temp_frame.vars[elem].value}\n")
        sys.stderr.write(f"\tPROCESSED INSTRUCTIONS COUNT: {self.processed_instructions}\n")
        sys.stderr.write(f"\tPOSITION IN CODE: {self.order_index + 1}\n")
        sys.stderr.write("\tCALL STACK:\n")
        if len(self.call_stack) != 0:
            sys.stderr.write("\t\t")
        for elem in self.call_stack:
            sys.stderr.write(f"{elem} - ")
        if len(self.call_stack) != 0:
            sys.stderr.write("\n")
        sys.stderr.write("\tHEAP:\n")
        for elem in self.heap:
            sys.stderr.write(f"\t\ttype: {elem.type},\tvalue: {elem.value}\n")
        sys.stderr.write("###############\n")
        self.order_index += 1

if '--help' in sys.argv and len(sys.argv) != 2:
    sys.exit(10)
parser = argparse.ArgumentParser(description='Skript (interpret.py v jazyce Python 3.10) načte XML reprezentaci programu a tento program s využitím vstupu dle parametrů příkazové řádky interpretuje a generuje výstup.')
parser.add_argument('--input', help='soubor se vstupy pro samotnou interpretaci zadaného zdrojového kódu')
parser.add_argument('--source', help='vstupní soubor s XML reprezentací zdrojového kódu')
args = parser.parse_args()

if args.input:
    input = args.input
    if not args.source:
        source = sys.stdin
if args.source:
    source = args.source
    if not args.input:
        input = sys.stdin
if not args.source and not args.input:
    sys.exit(10)

program = Program(source)
interpret = Interpret(program, input)
interpret.process_program()