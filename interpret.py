import xml.etree.ElementTree as ET
import sys
from collections import OrderedDict
from enum import Enum

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
                self.labels[" ".join(instr.find('arg1').text.strip().split())] = order
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
    
        

program = Program('test.xml')
test_value = Value()
test_value.set_value(Value.Types.INT, 5)
test_frame = Frame()
test_frame.add_var('count', test_value)
print(test_frame.get_var_value('count'))