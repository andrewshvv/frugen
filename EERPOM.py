#!/usr/bin/python3
# vi: set ts=4 sw=4 ai :
#
# $Id$
#
# (C) 2014, OAO T-Platforms, Russia

__author__ = 'andrey samokhvalov'
# -*- coding: utf-8 -*-

from debug import *
from bitarray import *
from collections import namedtuple
import datetime
import configparser

from LanguageCodes import *
from ChassisTypes import *
#==============================================================================
# Constants
#==============================================================================

MUL_OFFSET = 8
MUL_LENGTH = 8

BIT_RANGE = namedtuple("BitRange", "begin end")
RANGE_TYPE = BIT_RANGE(7, 6)
RANGE_LENGTH = BIT_RANGE(5, 0)
RANGE_FORMAT_VERSION = BIT_RANGE(3, 0)

# According to the IPMI FRU Standard version FOO
BEGIN_DATE = datetime.datetime(1996, 1, 1)

SUGGESTED_SIZE_COMMON_HEADER = 8
SUGGESTED_SIZE_INTERNAL_USE_AREA = 72
SUGGESTED_SIZE_CHASSIS_INFO_AREA = 32
SUGGESTED_SIZE_BOARD_INFO_AREA = 64
SUGGESTED_SIZE_PRODUCT_INFO_AREA = 80

INFO_FIELD_END_BYTE = 0xc1

LEN_NUMBER = 5
LEN_NAME = 30
LEN_INFO = 36
LEN_WIDTH = 8

BYTORDER = "big"

N_COMMON_HEADER = 0
N_INTERNAL_USE_AREA = 1
N_CHASSIS_INFO_AREA = 2
N_BOARD_INFO_AREA = 3
N_PRODUCT_INFO_AREA = 4


class Component:

    root = None
    name = None
    offset = None
    size = None
    isPresent = True

    def __init__(self, name="", size=0, offset=0):
        self.offset = offset
        self.name = name
        self.size = size
        self.isPresent = False

    def initFromBin(self, data):
        pass

    def initFromIni(self,config):
        pass

    def getOffset(self):
        pass

    def getSize(self):
        pass

    def getDescription(self):
        pass

    def setData(self, data):
        pass

    def getData(self):
        pass

    def reloadNode(self):
        pass

#==============================================================================
# Field Class
#==============================================================================
class Field(Component):

    number = None
    table = None
    data = None
    leftComponent = None

    def __init__(self, name="", size=0, offset=0):
        Component.__init__(self, name, size, offset)
        self.data = self.defaultData()

    def initFromBin(self, data):

        self.isPresent = True
        offset = self.getOffset()
        size = 0
        if isinstance(self, InfoField):
            size = self.getSize(data[offset:])
        else:
            size = self.getSize()

        self.data = data[offset:offset + size]

        return 0

    def defaultData(self):
        return b'\x00'

    def initFromIni(self,config):
        name = self.name.replace('/', '_')
        name = name.replace(' ', '_')
        config_variable_name = name.lower()

        try:
            config_string = config[config_variable_name]
            data = str.encode(config_string)
            self.userInput(data)

        except KeyError:
            return


    def getInfo(self):
        pass

    def getOffset(self):
        if self.leftComponent != None:
            if self.leftComponent != self.root:
                return self.leftComponent.getSize() + self.leftComponent.getOffset()
            else:
                return self.leftComponent.getOffset()

        return 0

    def setOffset(self, offset):
        self.offset = offset

    def getSize(self):
        return self.size

    def setSize(self, size):
        self.size = size

    def getData(self):
        return self.data

    def setData(self, data):
        self.data = data

    def userInput(self, data):
        e_print("command 'set' unsupported for this field")
        return

    def reloadNode(self):
        pass

    def getDescription(self):

        offset = LEN_INFO + LEN_NAME + LEN_NUMBER

        name_format = "%-" + str(LEN_NAME) + "s"
        info_format = "%-" + str(LEN_INFO) + "s"
        number_format = "%-" + str(LEN_NUMBER) + "s"

        format = number_format + name_format + info_format + "%s \n"
        description = format % (self.number, self.name, self.getInfo(), dataDescription(offset, self.getData(), LEN_WIDTH))


        return description

#==============================================================================
# Field Sub Classes
#==============================================================================
class FormatVersionField(Field):
    def defaultData(self):
        return b'\x01'

    def userInput(self, data):
        e_print("You can't change version field")
        return

    def getInfo(self):
        format_version_number = extract_data(self.getData(), RANGE_FORMAT_VERSION.begin, RANGE_FORMAT_VERSION.end)
        description = "%i" % (format_version_number)
        return description


class OffsetField(Field):
    def defaultData(self):
        return b'\x00'

    def userInput(self, data):
        e_print("Offset field changes automatically")
        return

    def getInfo(self):

        offset = extract_data(self.getData())
        description = "Multiple on %i = %i" % (MUL_OFFSET, MUL_OFFSET* offset)
        return description


class DataField(Field):
    def defaultData(self):
        return b''

    def userInput(self, data):
        self.setData(data)

    def getInfo(self):
        description = "%s" % (str(self.getData(),"iso-8859-1").replace("\x00", "\x20"))
        return description

    def getSize(self):
        return extract_data(self.size.getData(), RANGE_LENGTH.begin, RANGE_LENGTH.end)

    def setSize(self, size):
        self.size.setData(bytes([size]))

    def setData(self, data):
        data_len = len(data)
        field_size = self.getSize()
        max_len = self.root.getUnusedSpaceSize() + field_size

        while data_len >= max_len:
            table_size = self.root.getSize()
            self.root.setSize(table_size + 8)
            max_len = self.root.getUnusedSpaceSize() + field_size

        self.setSize(data_len)
        Field.setData(self, data)
        self.root.reloadNode()

class DateTimeField(Field):
    def userInput(self, data):
        self.setData(data)

    def getInfo(self):

        format = "%a %b %d %H:%M %Y"
        delta = datetime.timedelta(minutes=extract_data(self.getData()))
        mfg_time = BEGIN_DATE + delta

        description = "%s" % (mfg_time.strftime(format))
        return description

    def setData(self, data):

        date = data.decode("utf-8")
        format = "%H:%M %d.%m.%y"
        mfg_date = None

        try:
            mfg_date = datetime.datetime.strptime(date, format)
        except ValueError:
            e_print("format= %s" % 'H:M DD.MM.YY"')
            return

        delta = (mfg_date - BEGIN_DATE)
        min_delta = delta.days * 24 * 60 + delta.seconds // 60 + delta.seconds % 60
        self.data = min_delta.to_bytes(self.getSize(), BYTORDER)


class LengthField(Field):
    def defaultData(self):
        return b'\x02'

    def userInput(self, data):
        size = 0
        try:
            size = int(data.decode('utf-8'))

        except ValueError:
            e_print("Parameter must be a number")
            return

        self.setData(bytes([size]))

    def getInfo(self):
        byte_length = extract_data(self.getData())
        description = "Multiple on %i = %i" % (MUL_LENGTH, MUL_LENGTH * byte_length)
        return description

    def setData(self, data):

        size = int.from_bytes(data ,byteorder=BYTORDER)
        size = int(size / MUL_LENGTH) * MUL_LENGTH

        table_size = self.root.getSize()
        table_unused_space_size = self.root.getUnusedSpaceSize()

        isFirst = size < table_size
        isSecond = (table_size - size) > table_unused_space_size

        if isFirst & isSecond:

            min_size = table_size - (table_unused_space_size - (table_unused_space_size) % 8)
            e_print("You can set size > %i" % min_size)
            return

        self.data = bytes([int(size / MUL_LENGTH)])
        self.root.reloadNode()

class LanguageTypeField(Field):
    def userInput(self, data):
        self.setData(data)

    def getInfo(self):

        description = "Unknown"
        language_code = extract_data(self.getData())

        for lInfo in infoLanguageCodes:
            if int(lInfo['Code']) == language_code:
                description = lInfo['ShortName']
                break

        return description

    def setData(self, data):
        language_code = int(data.decode('utf-8'))
        self.data = bytes([language_code])
        self.root.reloadNode()

class TypeField(Field):

    def defaultData(self):
        return b'\xc0'

    def getInfo(self):
        type_code = extract_data(self.getData(), RANGE_TYPE.begin, RANGE_TYPE.end)
        str_len = extract_data(self.getData(), RANGE_LENGTH.begin, RANGE_LENGTH.end)
        description = "Type code: %i Data len: %i" % (type_code,str_len)
        return description

    def setData(self, data):
        self.data = set_data(self.data,data, RANGE_LENGTH.begin,RANGE_LENGTH.end)

class InfoField(Field):
    def defaultData(self):
        return bytes([INFO_FIELD_END_BYTE])

    def getSize(self, data=None):
        if data == None:
            data = self.getData()

        i=0
        byte = data[i]
        while(byte != INFO_FIELD_END_BYTE):
            i += 1
            byte = data[i]

        self.size = i + 1
        return self.size


class UnusedField(Field):
    def userInput(self, data):
        e_print("Unused field always must be filled with 0x00 bytes")
        return

    def getSize(self):
        field_offset = self.getOffset()
        table_offset = self.root.getOffset()
        table_size = self.root.getSize()

        used_space = field_offset - table_offset

        return table_size - used_space - 1

    def reloadNode(self):
        size = self.getSize()
        self.setData(b'\x00' * size)



class ChecksumField(Field):
    def userInput(self, data):
        e_print("Checksum field changes automatically")
        return

    def getInfo(self):
        data = extract_data(self.getData())
        description = "%i" % data
        return description

    def reloadNode(self):
        sum = 0
        i=0
        area_data = self.root.getData()
        chsm_pos = len(area_data) - 1

        while i < chsm_pos:
            sum += area_data[i]
            i += 1

        checksum = (sum % 256)
        checksum = 256 - checksum
        self.setData(bytes([checksum]))


class FirmwareField(Field):
    def getSize(self):

        field_offset = self.getOffset()
        table_offset = self.root.getOffset()
        table_size = self.root.getSize()

        used_space = field_offset - table_offset

        return table_size - used_space

class ChassisTypeField(Field):
    def userInput(self, data):
        self.setData(data)

    def getInfo(self):
        description = "Unknown"
        ch_code = extract_data(self.getData())

        for chInfo in infoChassisTypes:
            table_code = int.from_bytes(chInfo['Type'],byteorder=BYTORDER)
            if table_code == ch_code:
                description = chInfo['Info']
                break

        return description

    def setData(self, data):
        ch_type = int(data.decode('utf-8'))
        self.data = bytes([ch_type])

        self.root.reloadNode()

#==============================================================================
# Table Class
#==============================================================================
class Table(Component):

    componentsList = None
    checksum = None

    def __init__(self, name="", size=0, offset=0, checksum=None):

        Component.__init__(self, name, size, offset)
        self.componentsList = []
        self.checksum  = checksum

    def initFromBin(self, data):
        offset = self.getOffset()

        if offset == -1:
            return

        self.isPresent = True
        for component in self.componentsList:
            component.initFromBin(data)

    def initFromIni(self, config):
        try:
            config = config[self.name]
            self.isPresent = True

            for component in self.componentsList:
                component.isPresent = True

            for component in self.componentsList:
                component.initFromIni(config)

            self.reloadNode()

        except KeyError:
            return

    def addComponent(self, component):
        component.root = self
        component.number = len(self.componentsList)
        if len(self.componentsList) != 0:
            component.leftComponent = self.componentsList[-1]
        else:
            component.leftComponent = self

        self.componentsList += [component]

    def getUnusedSpaceSize(self):
        pass

    def getData(self):
        data = b''
        for component in self.componentsList:
            if component.isPresent:
                data = merge_data(data, component.getData())

        return data

    def getDescription(self):
        if self.isPresent == False:

            description =  "+" + "-"*31 + "+\n"
            description += "+ %-30s+\n" % (self.name + " NOT PRESENT")
            description += "+" + "-"*31 + "+\n"

            return description

        description =  "+" + "-"*31 + "+\n"
        description += "+ %-30s+\n" % self.name
        description += "+" + "-"*31 + "+\n"

        str_len = LEN_WIDTH + LEN_INFO + LEN_NAME + LEN_NUMBER

        number_format = "%-" + str(LEN_NUMBER) + "s"
        name_format = "%-" + str(LEN_NAME) + "s"
        info_format = "%-" + str(LEN_INFO) + "s"


        description += "="*str_len + "\n"
        description += (number_format + name_format + info_format + "%s \n") % ("N","NAME","INFO","DATA")
        description += "="*str_len + "\n"

        i=0
        for component in self.componentsList:
            description += component.getDescription()
            description += "\n"
            i+=1

        return description


#==============================================================================
# Table Sub Classes
#==============================================================================
class DynamicTable(Table):

    unused_field = None

    def __init__(self, name="", size=0, offset=0, checksum=None, unused_field=None):
        Table.__init__(self, name, size, offset, checksum)
        self.unused_field = unused_field

    def getOffset(self):
        offset = MUL_OFFSET * extract_data(self.offset.getData())
        if offset == 0:
            return -1
        else:
            return offset

    def setOffset(self, offset):
        data =  offset.to_bytes((self.offset.getSize()), byteorder=BYTORDER)
        self.offset.setData(data)

    def getSize(self):
        return MUL_LENGTH * extract_data(self.size.getData())

    def setSize(self, size):
        self.size.setData(bytes([size]))
        self.reloadNode()

    def getUnusedSpaceSize(self):
        return self.unused_field.getSize()

    def reloadNode(self):
        offset = 0x00
        for component in self.componentsList:
            component.reloadNode()

        for component in self.root.componentsList:
            if component.isPresent == False:
                continue

            size = int(component.getSize() / MUL_LENGTH)

            if size == 0:
                component.setOffset(0)

            component.setOffset(offset)
            offset += size

        commonHeader = self.root.componentsList[N_COMMON_HEADER]
        commonHeader.reloadNode()


class StaticTable(Table):

    def getSize(self):
        return self.size

    def setSize(self, size):
        self.size = size

    def setOffset(self, offset):
        self.offset = offset

    def getOffset(self):
        return self.offset

    def getUnusedSpaceSize(self):
        return 0

    def reloadNode(self):
        for component in self.componentsList:
            component.reloadNode()

class InternalUseAreaTable(DynamicTable):
    def getSize(self):

        internalOffset = self.getOffset()
        chassisOffset = self.root.componentsList[N_CHASSIS_INFO_AREA].getOffset()

        return chassisOffset - internalOffset


#==============================================================================
# Auxiliary functions
#==============================================================================
def dataDescription(offset, data, width):

    description = "|"
    ch = ''
    dataLen = len(data)
    i=0

    while i < dataLen:
        byte = data[i]
        ch = hex(byte)
        description +=  " %-4s" % ch

        if ((i + 1) % width == 0) & (i + 1 != dataLen):
            description += "\n" + " "*offset + "|"

        i += 1

    return description

def merge_data(first_data, second_data):

    f_array = bitarray()
    f_array.frombytes(first_data)

    s_array = bitarray()
    s_array.frombytes(second_data)

    return (f_array + s_array).tobytes()

def getbytes(data, start, end):

    array = bitarray()
    array.frombytes(data)

    length = array.length()
    bStart = length - start - 1
    bEnd = length - end

    # <-start     end->
    #  7 6 5 4 3 2 1 0
    # +---------------+
    # |0|0|1|0|1|1|1|1|
    # +---------------+

    peace = array[bStart:bEnd]

    pLen = peace.length()

    byte_len = 8
    rest = (byte_len - pLen) % byte_len

    zeroArr = bitarray(rest)
    zeroArr.setall(False)
    zeroArr += peace

    return zeroArr.tobytes()

def extract_data(data, start=-1, end=-1):
    if (start == -1) & (end == -1):
        return int.from_bytes(data, byteorder=BYTORDER)
    else:
        return int.from_bytes(getbytes(data, start, end), byteorder=BYTORDER)

def set_data(o_data, n_data, start, end):

        old_data = bitarray()
        old_data.frombytes(o_data)
        new_data = bitarray()
        new_data.frombytes(n_data)

        length = len(new_data)
        bStart = length - start - 1
        bEnd = length - end

        first_peace = old_data[:bStart]
        second_peace = old_data[bEnd:]

        ret_data = first_peace + new_data[length - (bEnd - bStart):] + second_peace
        return ret_data.tobytes()


def showChassisTypes():
    for chInfo in infoChassisTypes:
        print("%-4s - %-25s" % (int.from_bytes(chInfo["Type"], byteorder=BYTORDER), chInfo["Info"]))

def showLanguageTypes():
    for lInfo in infoLanguageCodes:
        print("{ShortName} {Code} {FullName}".format(**lInfo))

def initEERPOMTree():

# CAUTION: Before change field name see method Field.initFromIni
# example: Part Number type/length -> part_number_type_length

# name mangling variableType_tableName_[variableName]
# f - field
# t = table

#==============================================================================
# Init Common Header Table
#==============================================================================

    t_ch = StaticTable(name="Common Header",
                       size=SUGGESTED_SIZE_COMMON_HEADER)

    f_ch_format_version = FormatVersionField("Format Version", 1)
    f_ch_pad = Field("PAD", 1)
    f_ch_checksum = ChecksumField("Checksum", 1)
    f_ch_offset_iua = OffsetField("Internal Use Area Offset", 1)
    f_ch_offset_cia = OffsetField("Chassis Info Area Offset", 1)
    f_ch_offset_bia = OffsetField("Board Info Area Offset", 1)
    f_ch_offset_pia = OffsetField("Product Info Area Offset", 1)
    f_ch_offset_mria = OffsetField("Multi Record Area Offset", 1)

    t_ch.addComponent(f_ch_format_version)
    t_ch.addComponent(f_ch_offset_iua)
    t_ch.addComponent(f_ch_offset_cia)
    t_ch.addComponent(f_ch_offset_bia)
    t_ch.addComponent(f_ch_offset_pia)
    t_ch.addComponent(f_ch_offset_mria)
    t_ch.addComponent(f_ch_pad)
    t_ch.addComponent(f_ch_checksum)

#==============================================================================
# + Init Internal Use Area Table
#==============================================================================

    t_iua = InternalUseAreaTable(name="Internal Use Area", offset=f_ch_offset_iua)

    f_iua_format_version = FormatVersionField("Internal Use Format Version", 1)
    f_firm_data = FirmwareField("Firmware data")

    t_iua.addComponent(f_iua_format_version)
    t_iua.addComponent(f_firm_data)


#==============================================================================
# + Init Chassis Info Area Table
#==============================================================================

    f_cia_format_version = FormatVersionField("Format Version", 1)
    f_cia_len = LengthField("Length", 1)
    f_cia_type = ChassisTypeField("Chassis Type", 1)

    f_cia_part_numbers_len = TypeField("Part Number type/length", 1)
    f_cia_part_numbers_data = DataField("Part Number Data", size=f_cia_part_numbers_len)

    f_cia_serial_numbers_len = TypeField("Serial Number type/length", 1)
    f_cia_serial_numbers_data = DataField("Serial Number Data", size=f_cia_serial_numbers_len)

    f_cia_info_field = InfoField("Info fields")
    f_cia_unused_space = UnusedField("Any remaining unused space")
    f_cia_checksum = ChecksumField("Checksum", 1)


    t_cia = DynamicTable(name="Chassis Info Area",
                         offset=f_ch_offset_cia,
                         size=f_cia_len,
                         unused_field=f_cia_unused_space)

    t_cia.addComponent(f_cia_format_version)
    t_cia.addComponent(f_cia_len)
    t_cia.addComponent(f_cia_type)

    t_cia.addComponent(f_cia_part_numbers_len)
    t_cia.addComponent(f_cia_part_numbers_data)

    t_cia.addComponent(f_cia_serial_numbers_len)
    t_cia.addComponent(f_cia_serial_numbers_data)

    t_cia.addComponent(f_cia_info_field)

    t_cia.addComponent(f_cia_unused_space)
    t_cia.addComponent(f_cia_checksum)

#==============================================================================
# + Init Board Info Area Table
#==============================================================================

    f_bia_format_version = FormatVersionField("Format Version", 1)
    f_bia_len = LengthField("Length", 1)
    f_bia_language_code = LanguageTypeField("Language Code", 1)
    f_bia_mfg = DateTimeField("Mfg Date/Time", 3)

    f_bia_board_manufacturer_len = TypeField("Manufacturer type/length", 1)
    f_bia_board_manufacturer_data = DataField("Manufacturer Data", size=f_bia_board_manufacturer_len)

    f_bia_board_product_name_len = TypeField("Product Name type/length", 1)
    f_bia_board_product_name_data = DataField("Product Name Data", size=f_bia_board_product_name_len)

    f_bia_serial_number_len = TypeField("Serial Number type/length", 1)
    f_bia_serial_number_data = DataField("Serial Number Data", size=f_bia_serial_number_len)

    f_bia_part_number_len = TypeField("Part Number type/length", 1)
    f_bia_part_number_data = DataField("Part Number Data", size=f_bia_part_number_len)

    f_bia_fru_file_id_len = TypeField("FRU File ID type/length", 1)
    f_bia_fru_file_id_data = DataField("FRU File ID Data", size=f_bia_fru_file_id_len)

    f_bia_mfg_info_field = InfoField("Additional custom Mfg")

    f_bia_unused_space = UnusedField("Any remaining unused space")

    f_bia_checksum = ChecksumField("Checksum", 1)

    t_bia = DynamicTable("Board Info Area",
                         offset=f_ch_offset_bia,
                         size=f_bia_len,
                         unused_field=f_bia_unused_space)

    t_bia.addComponent(f_bia_format_version)
    t_bia.addComponent(f_bia_len)
    t_bia.addComponent(f_bia_language_code)
    t_bia.addComponent(f_bia_mfg)

    t_bia.addComponent(f_bia_board_manufacturer_len)
    t_bia.addComponent(f_bia_board_manufacturer_data)

    t_bia.addComponent(f_bia_board_product_name_len)
    t_bia.addComponent(f_bia_board_product_name_data)

    t_bia.addComponent(f_bia_serial_number_len)
    t_bia.addComponent(f_bia_serial_number_data)

    t_bia.addComponent(f_bia_part_number_len)
    t_bia.addComponent(f_bia_part_number_data)

    t_bia.addComponent(f_bia_fru_file_id_len)
    t_bia.addComponent(f_bia_fru_file_id_data)

    t_bia.addComponent(f_bia_mfg_info_field)

    t_bia.addComponent(f_bia_unused_space)

    t_bia.addComponent(f_bia_checksum)

#==============================================================================
# + Init Product Info Area Table
#==============================================================================

    f_pia_format_version = FormatVersionField("Format Version", 1)
    f_pia_len = LengthField("Length", 1)
    f_pia_language_code = LanguageTypeField("Language Code", 1)

    f_pia_manufacturer_name_len = TypeField("Manufacturer Name type/length", 1)
    f_pia_manufacturer_name_data = DataField("Manufacturer Name Data", f_pia_manufacturer_name_len)

    f_pia_name_len = TypeField("Product Name type/length", 1)
    f_pia_name_data = DataField("Product Name Data", f_pia_name_len)

    f_pia_product_part_number_len = TypeField("Part Number type/length", 1)
    f_pia_product_part_number_data = DataField("Part Number Data", f_pia_product_part_number_len)

    f_pia_product_version_len = TypeField("Version type/length", 1)
    f_pia_product_version_data = DataField("Version Data", f_pia_product_version_len)

    f_pia_serial_number_len  = TypeField("Serial Number type/length", 1)
    f_pia_serial_number_data = DataField("Serial Number Data", f_pia_serial_number_len)

    f_pia_asset_tag_len = TypeField("Asset Tag type/length", 1)
    f_pia_asset_tag_data = DataField("Asset Tag Data", f_pia_asset_tag_len)

    f_pia_fru_file_id_len = TypeField("FRU File ID type/length", 1)
    f_pia_fru_file_id_data = DataField("FRU File ID Data", f_pia_fru_file_id_len)

    f_pia_custom_info = InfoField("Custom product info area")

    f_pia_unused_space = UnusedField("Any remaining unused space" )

    f_pia_checksum = ChecksumField("Checksum", 1)

    t_pia = DynamicTable("Product Info Area",
                         offset=f_ch_offset_pia,
                         size=f_pia_len,
                         unused_field=f_pia_unused_space)

    t_pia.addComponent(f_pia_format_version)
    t_pia.addComponent(f_pia_len)
    t_pia.addComponent(f_pia_language_code)

    t_pia.addComponent(f_pia_manufacturer_name_len)
    t_pia.addComponent(f_pia_manufacturer_name_data)

    t_pia.addComponent(f_pia_name_len)
    t_pia.addComponent(f_pia_name_data)

    t_pia.addComponent(f_pia_product_part_number_len)
    t_pia.addComponent(f_pia_product_part_number_data)

    t_pia.addComponent(f_pia_product_version_len)
    t_pia.addComponent(f_pia_product_version_data)

    t_pia.addComponent(f_pia_serial_number_len)
    t_pia.addComponent(f_pia_serial_number_data)

    t_pia.addComponent(f_pia_asset_tag_len)
    t_pia.addComponent(f_pia_asset_tag_data)

    t_pia.addComponent(f_pia_fru_file_id_len)
    t_pia.addComponent(f_pia_fru_file_id_data)

    t_pia.addComponent(f_pia_custom_info)

    t_pia.addComponent(f_pia_unused_space)

    t_pia.addComponent(f_pia_checksum)


#==============================================================================
# + Init MultiRecord Area Table
#==============================================================================

    t_mria = DynamicTable("Multi Record Area", offset=f_ch_offset_mria)

#==============================================================================
# Create EERPOM table
#==============================================================================

    t_eerpom = StaticTable("EERPOM")

    t_eerpom.addComponent(t_ch)
    t_eerpom.addComponent(t_iua)
    t_eerpom.addComponent(t_cia)
    t_eerpom.addComponent(t_bia)
    t_eerpom.addComponent(t_pia)
    t_eerpom.addComponent(t_mria)

    return t_eerpom

def initFromBin(binFile):
    eerpom = initEERPOMTree()

    with open(binFile, 'rb') as fd:
        data = fd.read()
        eerpom.initFromBin(data)


    return eerpom

def initFromIni(iniFile):
    eerpom = initEERPOMTree()

    config = configparser.ConfigParser()
    config.read(iniFile)

    eerpom.isPresent = True
    for component in eerpom.componentsList:
        component.initFromIni(config)



    return eerpom