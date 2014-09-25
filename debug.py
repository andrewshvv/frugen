#!/usr/bin/python3
# vi: set ts=4 sw=4 ai :
#
# $Id$
#
# (C) 2014, OAO T-Platforms, Russia

__author__ = 'andrey samokhvalov'

__DEBUG__ = "Y"
def e_print(err):
    print("ERROR: " + err)

def d_print(debug_info):
    if(__DEBUG__ == "Y"):
        print(debug_info)

def p_print(prompt):
    print("PROMPT: " + prompt)