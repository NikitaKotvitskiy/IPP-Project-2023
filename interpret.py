import xml.etree.ElementTree as ET
import sys

opcodes = [ 'MOVE', 'CREATEFRAME', 'PUSHFRAME', 'POPFRAME', 'DEFVAR', 'CALL', 'RETURN',
            'PUSHS', 'POPS', 'ADD', 'SUB', 'MUL', 'IDIV', 'LT', 'GT', 'EQ', 'AND', 'OR', 'NOT',
            'INT2CHAR', 'STRI2INT', 'READ', 'WRITE', 'CONCAT', 'STRLEN', 'GETCHAR', 'SETCHAR', 'TYPE',
            'LABEL', 'JUMP', 'JUMPIFEQ', 'JUMPIFNEQ', 'EXIT', 'DPRINT', 'BREAK' ]   

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
        instructions = set(self.prog.findall('*'))
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
        return True

    def get_command(self, order):
        return None
    def get_atribute(self, order, attrib_num):
        return None


program = Program('test.xml')
if not program.check_xml():
    print('Bad')

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