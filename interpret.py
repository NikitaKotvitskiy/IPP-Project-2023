import xml.etree.ElementTree as ET
import sys
from collections import OrderedDict

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


program = Program('test.xml')
if not program.check_xml():
    print('Bad')
program.make_instructions_list()
print(program.get_instruction(5))
print(program.get_argument_type(5, 1))
print(program.get_argument_value(5, 1))

#tree = ET.parse('test.xml')
#root = tree.getroot()
#program = Program()
#for com in root.iter():
#    if (com.attrib['opcode'].upper == "LABEL"):
#        program.add_label(com.find('arg1'), int(com.attrib['order']))
#    command = Command(com.attrib['opcode'].upper)
#    for attr in com.iter:
#        Attribute = Attribute(attr.)
#    program.add_command()