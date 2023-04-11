<?php
/******************************************************************************
 *                                  IPP23
 *                                parser.php
 * 
 *                  Authors: Nikita Kotvitskiy (xkotvi01)
 * 
 *                        Last change: 13.03.23
 *****************************************************************************/


#Konstantní globální proměnné pro číselné kódy chyb
const MISSING_HEADER    = 21;
const BAD_OPPCODE       = 22;
const LEX_SYNTAX_ERROR  = 23;

#Konstantní globální proměnné pro práci s argumenty
const HELP_ARGUMENT = '--help';
const SCRIPT_HELP = "Skript typu filtr (parse.php v jazyce PHP 8.1) načte ze standardního vstupu zdrojový kód v IPP-code23, zkontroluje lexikální a syntaktickou správnost kódu a vypíše na standardní výstup XML reprezentaci programu.\n";

#Type příkazů IPPcode23. Používají se při zpracování argumentů příkazů
enum CommandTypes
{
    case none;
    case var;
    case var_symb;
    case label;
    case symb;
    case var_symb_symb;
    case var_type;
    case label_symb_symb;
}

#Stavy konečněho automatu pro kontrolu správnosti napsání připony proměnné
enum VarAnalysFSM
{
    case S;     #Stav START
    case GLT;   #Stav pro přečtení identifikátora návěští
    case F;     #Stav značící konec zpracování připony proměnné (dále se zpracovává jméno proměnné pomocí automaty NameAnalys)
};

#Stavy konečného automatu pro kontrolu správnosti napsání jména (proměnné nebo návěští)
enum NameAnalysFSM
{
    case S;         #Stav START
    case ALPHANUM;  #Stav pro přečtení alfanumerických znaků
    case SPECAIAL;  #Stav pro přečtení speciálního zymbolu na začátku jména
}; 

#Stavy konečného automatu pro kontrolu správnosti napsání literálu typu string
enum StringAnalysFSM
{
    case SYMBOLS;   #Stav pro přečtení normálních symbolů
    case ESQ;       #Stav pro přečtení ESQ sekvencí
};

#Class parser pro kontoulu správnostu napsání programu a generaci jeho XML reprezentace
class Parser
{
    #Pole, ve kterém identifikátory jednotlivých příkazů IPPcode23 jsou indexy elementů, obsahující typ těchto příkazů.
    #Typ příkazu určuje počet a význam očekavaných argumentů 
    private const COMMAND_ARRAY = array
    (
        "MOVE"          => CommandTypes::var_symb,
        "CREATEFRAME"   => CommandTypes::none,
        "PUSHFRAME"     => CommandTypes::none,
        "POPFRAME"      => CommandTypes::none,
        "DEFVAR"        => CommandTypes::var,
        "CALL"          => CommandTypes::label,
        "RETURN"        => CommandTypes::none,
        "PUSHS"         => CommandTypes::symb,
        "POPS"          => CommandTypes::var,
        "ADD"           => CommandTypes::var_symb_symb,
        "SUB"           => CommandTypes::var_symb_symb,
        "MUL"           => CommandTypes::var_symb_symb,
        "IDIV"          => CommandTypes::var_symb_symb,
        "LT"            => CommandTypes::var_symb_symb,
        "GT"            => CommandTypes::var_symb_symb,
        "EQ"            => CommandTypes::var_symb_symb,
        "AND"           => CommandTypes::var_symb_symb,
        "OR"            => CommandTypes::var_symb_symb,
        "NOT"           => CommandTypes::var_symb_symb,
        "INT2CHAR"      => CommandTypes::var_symb,
        "STRI2INT"      => CommandTypes::var_symb_symb,
        "READ"          => CommandTypes::var_type,
        "WRITE"         => CommandTypes::symb,
        "CONCAT"        => CommandTypes::var_symb_symb,
        "STRLEN"        => CommandTypes::var_symb,
        "GETCHAR"       => CommandTypes::var_symb_symb,
        "SETCHAR"       => CommandTypes::var_symb_symb,
        "TYPE"          => CommandTypes::var_symb,
        "LABEL"         => CommandTypes::label,
        "JUMP"          => CommandTypes::label,
        "JUMPIFEQ"      => CommandTypes::label_symb_symb,
        "JUMPIFNEQ"     => CommandTypes::label_symb_symb,
        "EXIT"          => CommandTypes::symb,
        "DPRINT"        => CommandTypes::symb,
        "BREAK"         => CommandTypes::none,
    );

    #Pole pro speciální symbolu, které se mohou vyskitovat na začátku jména proměnných nebo návěští
    private const SPECIAL_CHARACTERS = array("_", "-", "$", "%", "*", "!", "?");
    private const TYPES = array("nil", "int", "bool", "string");
    private const IPPcode23Header = ".ippcode23";

    #Tato proměnná obsahuje XML reprezentaci programu
    private $xml;
    #Tato proměnná obahuje pořadkové číslo příkazu, který momentálně zpracováváme
    private $commandCounter;
    #Tato pomocná proměnná obsahuje odkaz na aktuální XML element
    private $currentCommandElement;
    #Tato pomocná proměnná obsahuje pořadkové číslo argumentu pŕíkazum který momentálně zpracováváme
    private $currentCommandArgumentsCount;

    #Nastavuje počateční hodnoty pomocných proměnných, vatváří XML objekt
    public function ParserConstructor()
    {
        $this->xml = new SimpleXMLElement('<?xml version="1.0" encoding="UTF-8"?><program/>');
        $this->xml->addAttribute('language', 'IPPcode23');
        $this->commandCounter = 1;
        $this->currentCommandArgumentsCount = 0;
    }

    #Zpracovává program
    public function ParseProgram($source)
    {
        #Načtení hlavičky
        while (true)
        {
            $line = trim(fgets($source));
            if (str_contains($line, '#'))
                $line = substr($line, 0, strpos($line, "#"));
            if ($line == "")
                continue;
            break;
        }
        $this->CheckHeaderLine($line);

        #Načtení a zpracování jednotlivých příkazů
        while (!feof(STDIN))
        {
            $line = trim(fgets($source));
            $this->ProcessCommand($line);
        }

        #Výpis XML documentu na výstup
        $output = $this->xml->asXML();
        echo $output;
    }

    #Kontrola správnosti hlavičky
    private function CheckHeaderLine(string $line)
    {   
        if (strtolower(substr($line, 0, strlen(self::IPPcode23Header))) == self::IPPcode23Header)
            return true;
        exit(MISSING_HEADER);
    }

    #Zpracování příkazu
    private function ProcessCommand(string $line)
    {
        #Odstánění komentářů
        if (str_contains($line, '#'))
            $line = trim(substr($line, 0, strpos($line, "#")));

        #Rozdělení na jednotlivé lexemy
        $command = preg_split("/[\s]+/", $line);
        if ($command[0] == "")
            return;

        #Vytváření nového elementu "instruction" a kontrola správnosti příkazu
        $this->currentCommandElement = $this->CreateCommandElement($command[0]);
        if (!array_key_exists($command[0], self::COMMAND_ARRAY))
            exit(BAD_OPPCODE);

        #Zpracování argumentů příkazu
        switch (self::COMMAND_ARRAY[$command[0]])
        {
            case CommandTypes::none:
                $this->CheckArgumentCount(0, $command);
                break;
            case CommandTypes::var:
                $this->CheckArgumentCount(1, $command);
                $var = $command[1];
                if (!$this->CheckVar($var)) exit(LEX_SYNTAX_ERROR);
                
                break;
            case CommandTypes::var_symb:
                $this->CheckArgumentCount(2, $command);
                $var = $command[1];
                $symb = $command[2];
                if (!$this->CheckVar($var)) exit(LEX_SYNTAX_ERROR);
                if (!$this->CheckSymb($symb)) exit(LEX_SYNTAX_ERROR);
                break;
            case CommandTypes::label:
                $this->CheckArgumentCount(1, $command);
                $label = $command[1];
                if (!$this->CheckLabel($label)) exit(LEX_SYNTAX_ERROR);
                break;
            case CommandTypes::symb:
                $this->CheckArgumentCount(1, $command);
                $symb = $command[1];
                if (!$this->CheckSymb($symb)) exit(LEX_SYNTAX_ERROR);
                break;
            case CommandTypes::var_symb_symb:
                $this->CheckArgumentCount(3, $command);
                $var = $command[1];
                $symb1 = $command[2];
                $symb2 = $command[3];
                if (!$this->CheckVar($var)) exit(LEX_SYNTAX_ERROR);
                if (!$this->CheckSymb($symb1)) exit(LEX_SYNTAX_ERROR);
                if (!$this->CheckSymb($symb2)) exit(LEX_SYNTAX_ERROR);
                break;
            case CommandTypes::var_type:
                $this->CheckArgumentCount(2, $command);
                $var = $command[1];
                $type = $command[2];
                if (!$this->CheckVar($var)) exit(LEX_SYNTAX_ERROR);
                if ($this->CheckType($type) == "none") exit (LEX_SYNTAX_ERROR);
                $this->AddCommandArgument('type', $type);
                break;
            case CommandTypes::label_symb_symb:
                $this->CheckArgumentCount(3, $command);
                $label = $command[1];
                $symb1 = $command[2];
                $symb2 = $command[3];
                if (!$this->CheckLabel($label)) exit(LEX_SYNTAX_ERROR);
                if (!$this->CheckSymb($symb1)) exit(LEX_SYNTAX_ERROR);
                if (!$this->CheckSymb($symb2)) exit(LEX_SYNTAX_ERROR);
                break;
            default:
                exit(BAD_OPPCODE);
        }
        $this->currentCommandArgumentsCount = 0;
    }

    #Vytváření nového XML elementu "instruction"
    private function CreateCommandElement($opcode)
    {
        $newInstr = $this->xml->addChild('instruction');
        $newInstr->addAttribute('order', "$this->commandCounter");
        $this->commandCounter++;
        $newInstr->addAttribute('opcode', "$opcode");
        return $newInstr;
    }
    
    #Vytváření nového XML elementu "arg[num]"
    private function AddCommandArgument($type, $value)
    {
        $this->currentCommandArgumentsCount++;
        $arg = $this->currentCommandElement->addChild("arg$this->currentCommandArgumentsCount", $value);
        $arg->addAttribute('type', $type);
    }

    #Kontola počtu argumentů příkazu
    private function CheckArgumentCount(int $neededCount, array $command)
    {
        $argCount = count($command) - 1;
        if ($argCount != $neededCount)
            exit(LEX_SYNTAX_ERROR);
    }

    #Kontola správnosti napsání proměnné
    private function CheckVar(string $str) : bool
    {
        $strArr = str_split($str);
        $state = VarAnalysFSM::S;
        foreach ($strArr as $char)
        {
            switch ($state)
            {
                case VarAnalysFSM::S:
                    if ($char == 'G' || $char == 'L' || $char == 'T')
                    {
                        $state = VarAnalysFSM::GLT;
                        break;
                    }
                    return false;
                case VarAnalysFSM::GLT:
                    if ($char == 'F')
                    {
                        $state = VarAnalysFSM::F;
                        break;
                    }
                    return false;
                case VarAnalysFSM::F:
                    if ($char == '@')
                    {
                        if (!$this->CheckName($strArr, 3))
                            return false;
                        break 2;
                    }
                    return false;
            }
        }
        $this->AddCommandArgument('var', $str);
        return true;
    }

    #Kontola správnosti napsání symbolu (v podstatě, buď literálu, nebo proměnné)
    private function CheckSymb(string $symb) : bool
    {
        if ($this->CheckLiteral($symb) || $this->CheckVar($symb))
            return true;
        return false;
    }

    #Kontola správnosti napsání návéští
    private function CheckLabel(string $label)
    {
        if (!$this->CheckName(str_split($label), 0))
            return false;

        $this->AddCommandArgument('label', $label);
        return true;
    }

    #Kontola správnosti napsání typu
    private function CheckType(string $type) : string
    {
        if (!in_array($type, self::TYPES))
            return "none";

        return $type;
    }
    
    #Kontola správnosti napsání jména proměnné nebo návěští 
    private function CheckName(array $stringWithName, int $startPos) : bool
    {
        $state = NameAnalysFSM::S;
        for ($i = $startPos; $i < count($stringWithName); $i++)
        {
            $symbol = $stringWithName[$i];
            switch ($state)
            {
                case NameAnalysFSM::S:
                    if (ctype_alnum($symbol))
                    {
                        $state = NameAnalysFSM::ALPHANUM;
                        break;
                    }
                    if (in_array($symbol, SPECIAL_CHARACTERS))
                    {
                        $state = NameAnalysFSM::SPECAIAL;
                        break;
                    }
                    return false;
                case NameAnalysFSM::SPECAIAL:
                    if (ctype_alnum($symbol))
                    {
                        $state = NameAnalysFSM::ALPHANUM;
                        break;
                    }
                    return false;
                case NameAnalysFSM::ALPHANUM:
                    if (ctype_alnum($symbol))
                        break;
                    return false;
            }
        }
        return true;
    }
    
    #Kontola správnosti napsání literálu
    private function CheckLiteral(string $literal) : bool
    {
        $literal = str_split($literal);
        $atsignPosition = array_search("@", $literal);
        if (!$atsignPosition)
            return false;
        $type = $this->CheckType(implode(array_slice($literal, 0, $atsignPosition)));
        $value = implode(array_slice($literal, $atsignPosition + 1, count($literal) - 1));

        switch ($type)
        {
            case "none":
                return false;
            case "nil":
                if ($value != "nil")
                return false;
                break;
            case "int":
                if (!is_numeric($value))
                return false;
                break;
            case "bool":
                if ($value != "true" && $value != "false")
                    return false;
                break;
            case "string":
                $this->CheckString($value);
                break;
        }
        $this->AddCommandArgument($type, $value);
        return true;
    }

    #Kontola správnosti napsání literálu typu string
    private function CheckString(string $value)
    {
        $value = str_split($value);
        $state = StringAnalysFSM::SYMBOLS;
        $esqCnt = 0;
        $esqNum = "";
        for ($i = 0; $i < count($value); $i++)
        {
            switch ($state)
            {
                case StringAnalysFSM::SYMBOLS:
                    if ($value[$i] == "\\")
                    {
                        $state = StringAnalysFSM::ESQ;
                        if ($i == count($value) - 1)
                            exit(LEX_SYNTAX_ERROR);
                    }
                    break;
                case StringAnalysFSM::ESQ:
                    if (!is_numeric($value[$i]))
                        exit(LEX_SYNTAX_ERROR);
                    $esqNum .= $value[$i];
                    $esqCnt++;
                    if ($esqCnt == 3)
                    {
                        $esqNum = intval($esqNum);
                        if ($esqNum >= 0 && $esqNum <= 32 || $esqNum == 35 || $esqNum == 92)
                        {
                            $state = StringAnalysFSM::SYMBOLS;
                            $esqNum = "";
                            $esqCnt = 0;
                            break;
                        }
                        exit(LEX_SYNTAX_ERROR);
                    }
                    else if ($i == count($value) - 1)
                        exit(LEX_SYNTAX_ERROR);
                    break;
            }   
        }
    }
}

CheckArguments($argv);
$parser = new Parser();
$parser->ParserConstructor();
$parser->ParseProgram(STDIN);

function CheckArguments($argv)
{
    if (count($argv) == 2 && $argv[1] == HELP_ARGUMENT)
    {
        echo SCRIPT_HELP;
        exit(0);
    }
    else if (count($argv) >= 2)
        exit(1);
}
?>