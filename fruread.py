#!/usr/bin/python3
# vi: set ts=4 sw=4 ai :
#
# $Id$
#
# (C) 2014, OAO T-Platforms, Russia
#
# This utility can read and write FRU images prepared according to the IPMI FRU Standard version FOO

__author__ = 'andrey samokhvalov'
# -*- coding: utf-8 -*-


from cmd import Cmd
from debug import *
import EERPOM
import argparse
import shlex
import sys


STR_PRELOAD = "+=============================================+ \n" \
              "|                                             | \n" \
              "|                                             | \n" \
              "|            FRU binary generator 1.0          | \n" \
              "|                                             | \n" \
              "|                                             | \n" \
              "+=============================================+ \n"


STR_POSTLOAD = "Bye Bye! \n"
STR_PROMPT = "frugen> "
DEBUG_PROMT = "N"

class Interpreter(Cmd):

    stop = None
    table = None

    def __init__(self,eerpom):
        Cmd.__init__(self)

        self.eerpom = eerpom
        self.table = eerpom
        self.stop = False
        self.prompt = STR_PROMPT

    def preloop(self):
        print(STR_PRELOAD)
        self.do_list()

    def postloop(self):
        print(STR_POSTLOAD)

    def postcmd(self, stop, line):
        return self.stop

    def do_quit(self, *args):
        'quit from fru command line'
        self.stop = True



    def do_set(self, *args):
        'set [number data] - set data to the field'

        args = shlex.split(args[0])
        length = len(args)

        if length == 0:
            self.do_list()
            return

        elif length == 1:
            self.do_list()
            return

        elif length == 2:

            component = None
            string = None

            try:
                number = int(args[0])
                string = args[1]

                component = self.table.componentsList[number]

            except IndexError:
                self.do_list()
                return

            except ValueError:
                EERPOM.p_print("Not correct value")
                return

            if isinstance(component,EERPOM.Table):
                p_print("That is table")
                return

            component.userInput(str.encode(string))
            return

        elif length > 2:
            self.do_help("set")
            return

    def do_back(self, *args):
        'back to  previous menu'
        if self.table.root != None:
            self.table = self.table.root
            self.do_list()

    def do_choose(self, *args):
        'choose [ number ] - Transition to the selected sub-menu'

        args = shlex.split(args[0])
        length = len(args)

        if length == 0:
            self.do_list()
            return

        elif length == 1:
            number = None
            component = None

            try:
                number = int(args[0])
                component = self.table.componentsList[number]

            except IndexError:
                self.do_list()
                return

            except ValueError:
                EERPOM.p_print("Incorrect value")
                return

            if isinstance(component, EERPOM.Field):
                p_print("This is a field")
                return

            if component.isPresent:
                self.table = component
                self.do_list()
            else:
                self.do_show(str(number))

        else:
            return 0


    def do_list(self, *args):
        'list all sub-menu, you can use 1. choose [number] or 2. show [number]'

        i = 0
        for component in self.table.componentsList:
            print("%i: %-20s"  % (i, component.name))
            # print component
            i += 1

    def do_show(self, *args):
        'show [number]  - get description for sub-menu'

        args = shlex.split(args[0])
        length = len(args)

        description = ""
        if length == 0:
            description = self.table.getDescription()
            print(description)
            return

        elif length == 1:
            number = None
            component = None

            try:
                number = int(args[0])
                component = self.table.componentsList[number]

            except IndexError:
                self.do_list()
                return
            except ValueError:
                EERPOM.p_print("Incorrect value")
                return

            description = component.getDescription()
            print(description)


    def do_save(self, *args):
        'save file_path - save fru binary '

        args = shlex.split(args[0])
        length = len(args)

        if length == 0:
            self.do_help("save")
            return

        elif length == 1:

            self.eerpom.reloadNode()
            with open(args[0],"wb+") as f:
                data = self.eerpom.getData()
                f.write(data)

            return

    def do_info(self,*args):
        'info ct- for chassis types \ninfo lc- for language codes'

        args = shlex.split(args[0])
        length = len(args)

        if length == 0:
            self.do_help("info")
            return

        elif length == 1:
            info_type = args[0]
            if info_type == 'ct':
                EERPOM.showChassisTypes()

            elif info_type == 'lc':
                EERPOM.showLanguageTypes()

            else:
                self.do_help("info")

            return

        else:
            self.do_help("info")
            return

        print(EERPOM.showChassisTypes())


    def complete_info(self, *args):
        #автодополнение команды info TODO
        return



#==============================================================================
# Parse arguments
#==============================================================================

argsList = argparse.ArgumentParser(description="FRU Information Storage image generator")
argsList.add_argument("-t", dest="type", help="bin - for binary file ,  ini - for ini file", type=str, required=True)
argsList.add_argument("-f", dest="file", help="path to the FRU file", type=str, required=True)
argsList.add_argument("-c", dest="commands",help="Text file with interpreter's commands", type=str, default=None, required=False)


options = argsList.parse_args()
options = vars(options)

#==============================================================================
# Init EERPOM from file
#==============================================================================

eerpom = None

dataFile = options['file']
type = options['type']

if type == 'bin':
    eerpom = EERPOM.initFromBin(dataFile)

elif type == 'ini':
    eerpom = EERPOM.initFromIni(dataFile)

else:
    sys.exit("Incorrect type of file")



#==============================================================================
# Start cmd loop
#==============================================================================

interpreter = Interpreter(eerpom)
commandsFile = options['commands']

if commandsFile != None:
    with open(commandsFile,'r') as f:
        commands = f.read()
        commands = commands.split('\n')

        for command in commands:
            interpreter.onecmd(command)
else:
    interpreter.cmdloop()

