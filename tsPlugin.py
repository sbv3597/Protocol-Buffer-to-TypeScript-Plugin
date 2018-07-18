#!/usr/bin/env python
# tsPlugin.py is the plugin compiler to generate the TypeScript code for the corresponding protocol buffer code
import sys
import json
from google.protobuf.compiler import plugin_pb2 as plugin
from google.protobuf.descriptor_pb2 import DescriptorProto, EnumDescriptorProto, ServiceDescriptorProto

# Data Types corresponding to the parsed numerical values for datatypes generated by google.protobuf.compiler
DataType = { 
    1: "number", 2: "number", 3: "number", 4: "number", 5: "number",
    6: "number", 7: "number", 8: "boolean", 9: "string", 10: "Group",
    11: "Message", 12: "string", 13: "number", 14: "Enum", 15: "number", 
    16: "number", 17: "number", 18: "number", 19: "number",
}

# Using Predefined key words
Predefined = {
    "break": "_break", "case": "_case", "catch": "_catch", "class": "_class", "const": "_const", "continue": "_continue",
    "debugger": "_debugger", "default": "_default", "delete": "_delete", "do": "_do", "else": "_else", "enum": "_enum",
    "export": "_export", "extends": "_extends", "false": "_false", "finally": "_finally", "for": "_for", "function": "_function",
    "if": "_if", "import": "_import", "in": "_in", "instanceof": "_instanceof", "new": "_new", "null": "_null",
    "return": "_return", "super": "_super", "switch": "_switch", "this": "_this", "throw": "_throw", "true": "_true",
    "try": "_try", "typeof": "_typeof", "var": "_var", "void": "void", "while": "_while", "with": "_with",
    "implements": "_implements", "interface": "_interface", "let": "_let", "package": "_package", "private": "_private", "protected": "_protected",
    "public": "_public", "static": "_static", "yield": "_yield", "any": "_any", "boolean": "_boolean", "number": "_number",
    "string": "_string", "symbol": "_symbol", "abstract": "_abstract", "as": "_as", "async": "_async", "await": "_await",
    "constructor": "_constructor", "declare": "_declare", "from": "_from", "get": "_get", "is": "_is", "module": "_module",
    "namespace": "_namespace", "of": "_of", "require": "_require", "set": "_set", "type": "type", "readonly": "_readonly"
}

# Custom Types [ <first>: input_parameter, <second>: output_observable] translated in typesript format
CustomType = {
    "Empty": ["", "void"], 
    "Timestamp": ["number","number"], 
    "Duration": ["number","number"],
    "Any": ["any","any"],
}

# Ignored Imports are the imports for which we are providing custom types
ImportIgnore = [
    "GoogleProtobuf",
]

# Package stores all the package name of the provided files including the imported files corresponding to their file name
PackAge = {}

# dictPackage keys all the packages that are called in
dictPackage = {} 
# dictImports stores all the classes, enums, and interfaces for a package
dictDeclarations = {}
# unassigned file name
FirstFile = "not assigned"
ImportMap = {}

# check for Predefined keywords
def checkPredefined(name):
    if name in Predefined:
        name = Predefined[name]
    return name

# Output File Name
def fileName(nameWithExt):
    seg = nameWithExt.split('.')
    no = len(seg)
    nameWithoutExt = seg[0]
    for i in range(1,no-1):
        nameWithoutExt+="."+seg[i]
    return nameWithoutExt

# imported variable name case handling 
def importVariable(name):
    seg = name.split('.')
    name = ""
    for i in seg:
        i = i[0].upper() + i[1:]
        name += i
    return name

# interface name case handling 
def interfaceName(full_name):
    seg = full_name.split('.')
    name = seg[len(seg)-1]
    package = seg[1]
    i = 2
    while (i < len(seg)-1):
        package += "." + seg[i]
        i = i + 1
    package = importVariable(package)
    return name, package

# variable name case handling
def variableName(name):
    seg = name.split('_')
    res = ""
    no = len(seg)
    for i in range(no):
        if i != 0:
            seg[i] = seg[i][0].upper() + seg[i][1:]
        res+=seg[i]
    return res

# function name case handling
def functionName(name):
    name = name[0].lower() + name[1:]
    return name

# fucntion parameter case handling
def functionParameter(name):
    name = name[0].lower()+name[1:]
    return name

# parametersTypes returns the Function input Parameters
def parametersTypes(proto_package, full_name):
    name, package = interfaceName(full_name)
    imprt = ""
    if name in CustomType:
        if CustomType[name][0] == "":
            return "", imprt
        else:
            return checkPredefined(functionParameter(name)) + ": " + CustomType[name][0], imprt
    else:
        inface = name
        if package != proto_package:
            # inface = package + "." + checkPredefined(inface)
            # return checkPredefined(functionParameter(name)) + ": " + checkPredefined(inface)
            imprt = "import {" + inface + "} from  './" + package.lower() + ".service'\n"
        return checkPredefined(functionParameter(name)) + ": " + checkPredefined(inface), imprt

# returnTypes returns Function output Parameters
def returnTypes(proto_package, full_name):
    name, package = interfaceName(full_name)
    imprt = ""
    #return full_name
    if name in CustomType:
        return CustomType[name][1], imprt
    else:
        if package != proto_package:
            # name = package + "." + checkPredefined(name)
            # return name
            imprt = "import {" + name + "} from  './" + package.lower() + ".service'\n"
        return name, imprt

# nestedTypes returns the nested declarations of enums and message 
def nestedTypes(proto_file, proto_package):
    # Nested Enums
    Enums = ""
    for enm in proto_file.enum_type:
        Enums += "export enum " + checkPredefined(enm.name) + " {\n"
        for v in enm.value:
            Enums += "\t" + checkPredefined(str(v.name)) + " = " + str(v.number) + ",\n"
        Enums += "}\n\n"

    # Nested Inerfaces
    Interfaces = ""
    for msg in proto_file.nested_type:
        if msg.options.map_entry == True:
            return Enums + Interfaces
        Interfaces += nestedTypes(msg, proto_package)
        Interfaces += "export interface " + checkPredefined(msg.name) + " {\n"
        for f in msg.field:
            dtype = DataType[f.type]
            vtype = ""
            if dtype == "Message" or dtype == "Enum":
                dtype, package = interfaceName(f.type_name)
                dtype = checkPredefined(dtype)
                if dtype in CustomType:
                    dtype = CustomType[dtype][0]
                else:
                    if package != proto_package and package != str(proto_package) + msg.name:
                        vtype = dtype
                        # dtype = package + "." + dtype
                        if proto_package == PackAge[FirstFile]:
                            ImportMap["import {" + dtype + "} from  './" + package.lower() + ".service'\n"] = 1
             
            # handling oneof case of protobuf as like union in c/c++
            oneOf = ""
            if str(f).find('oneof_index') != -1:
                oneOf = "?"
            # if Repeated
            ary = ""
            if f.label == 3:
                ary = "[]"
            no = len(dtype)
            if ary != "" and dtype[no-5:] == "Entry":
                val="{\n\t\t"
                for nes in msg.nested_type:
                    if vtype == nes.name:
                        dtype = vtype
                    if nes.name == dtype:
                        for nf in nes.field:
                            if nf.name == "key":
                                ty = DataType[nf.type]
                                val += "[key: " + ty + "]: "
                                break
                        for nf in nes.field:
                            if nf.name == "value":
                                ty = DataType[nf.type]
                                if ty == "Message" or ty == "Enum":
                                    ty, package = interfaceName(nf.type_name)
                                    ty = checkPredefined(ty)
                                    if ty in CustomType:
                                        ty = CustomType[ty][0]
                                    else:
                                        if package != proto_package and package != str(proto_package) + msg.name:
                                            # ty = package + "." + ty
                                            if proto_package == PackAge[FirstFile]:
                                                ImportMap["import {" + ty + "} from  './" + package.lower() + ".service'\n"] = 1
                                val += ty + ";\n\t}"
                                break
                dtype = val
                ary=""
            Interfaces += "\t" + variableName(f.name) + str(oneOf) + ": " + dtype + ary + ";\n"
            # in case if a TypeScript keyword check is required in variable name of an interface
            # Interfaces += "\t" + checkPredefined(variableName(f.name)) + str(oneOf) + ": " + dtype + ary + ";\n"
        Interfaces += "}\n\n"

    return Enums + Interfaces


# Final TypeScript code generator
def generateCode(request, response):
    # Generate Package
    for proto_file in request.proto_file:
        PackAge[str(proto_file.name)] = str(proto_file.package)

    
    FirstFile = str(request.proto_file[-1].name)

    # Parse requests
    for proto_file in request.proto_file:
        # File Name and Package
        proto_file_name = fileName(str(proto_file.name))
        proto_package = importVariable(PackAge[str(proto_file.name)])

        # Stores Imports 
        # Imports = ""
        # for imp in proto_file.dependency:
        #     importName = importVariable(PackAge[imp])
        #     if importName not in ImportIgnore and importName != proto_package:
        #         ImportMap["import * as " + checkPredefined(importName) + " from './" + PackAge[imp].lower() + ".service'\n"] = 1
        #         #Imports += "import * as " + checkPredefined(importName) + " from './" + PackAge[imp].lower() + ".service'\n"
        
        # Stores Enums
        Enums = ""
        for enm in proto_file.enum_type:
            Enums += "export enum " + checkPredefined(enm.name) + " {\n"
            for v in enm.value:
                Enums += "\t" + checkPredefined(str(v.name)) + " = " + str(v.number) + ",\n"
            Enums += "}\n\n"

        # Stores Interfaces
        Interfaces = ""
        for msg in proto_file.message_type:
            Interfaces += "export interface " + checkPredefined(msg.name) + " {\n"
            for f in msg.field:
                dtype = DataType[f.type]
                vtype = ""
                if dtype == "Message" or dtype == "Enum":
                    dtype, package = interfaceName(f.type_name)
                    dtype = checkPredefined(dtype)
                    if dtype in CustomType:
                        dtype = CustomType[dtype][0]
                    else:
                        if package != proto_package and package != str(proto_package) + msg.name:
                            vtype = dtype
                            # dtype = package + "." + dtype
                            if proto_package == PackAge[FirstFile]:
                                ImportMap["import {" + dtype + "} from  './" + package.lower() + ".service'\n"] = 1
                
                # handling oneof case of protobuf as like union in c/c++
                oneOf = ""
                if str(f).find('oneof_index') != -1:
                    oneOf = "?"
                # if Repeated
                ary = ""
                if f.label == 3: # 3 for LABEL_REPEATED
                    ary = "[]"
                no = len(dtype)
                if ary != "" and dtype[no-5:] == "Entry":
                    val="{\n\t\t"
                    for nes in msg.nested_type:
                        if vtype == nes.name:
                            dtype = vtype
                        if nes.name == dtype:
                            for nf in nes.field:
                                if nf.name == "key":
                                    ty = DataType[nf.type]
                                    val += "[key: " + ty + "]: "
                                    break
                            for nf in nes.field:
                                if nf.name == "value":
                                    ty = DataType[nf.type]
                                    if ty == "Message" or ty == "Enum":
                                        ty, package = interfaceName(nf.type_name)
                                        ty = checkPredefined(ty)
                                        if ty in CustomType:
                                            ty = CustomType[ty][0]
                                        else:
                                            if package != proto_package and package != str(proto_package) + msg.name:
                                                # ty = package + "." + ty
                                                if proto_package == PackAge[FirstFile]:
                                                    ImportMap["import {" + ty + "} from  './" + package.lower() + ".service'\n"] = 1
                                    val += ty + ";\n\t}"
                                    break
                    dtype = val
                    ary=""
                Interfaces += "\t" + variableName(f.name) + str(oneOf) + ": " + dtype + ary + ";\n"                
                # in case if a TypeScript keyword check is required in variable name of an interface
                # Interfaces += "\t" + checkPredefined(variableName(f.name)) + str(oneOf) + ": " + dtype + ary + ";\n"
            Interfaces += "}\n\n"
            Interfaces += nestedTypes(msg, proto_package)

        # Stores Classes
        Classes = "" 
        for service in proto_file.service:
            Classes += "export abstract class Service" + service.name + " {\n"
            for m in service.method:
                par, imprt = parametersTypes(proto_package, m.input_type)
                if imprt != "":
                    if proto_package == PackAge[FirstFile]:
                        ImportMap[imprt] = 1
                ret, imprt = returnTypes(proto_package, m.output_type)
                if imprt != "":
                    if proto_package == PackAge[FirstFile]:
                        ImportMap[imprt] = 1
                Classes += "\tabstract " + checkPredefined(functionName(m.name)) + "(" + par + "): Observable<" + checkPredefined(ret) + ">;\n"
            Classes += "}\n\n"
    
        # proto_package will acts as the key to store all imports, classes, enums, and interfaces of all files with same package name
        key = proto_package
        if key not in dictPackage:
            dictPackage[key] = True
            dictDeclarations[key] = Classes + Enums + Interfaces
        else:
            dictPackage[key] = True
            dictDeclarations[key] += Classes + Enums + Interfaces

    # Fill responses in TypeScript corresponding to the proto::buffer
    key = importVariable(PackAge[FirstFile])
    f = response.file.add()
    name = key[0].lower()
    for i in range(1,len(key)):
        if key[i].isupper():
            name += "."
        name += key[i].lower()
    f.name = name + ".service.ts"
    f.content = "import { Observable } from 'rxjs';\n" 
    for i in ImportMap:
        f.content += i
    f.content += "\n" + dictDeclarations[key]

# Main CallBack
if __name__ == '__main__':
    # Read request message from stdin
    data = sys.stdin.read()

    # Parse request
    request = plugin.CodeGeneratorRequest()
    request.ParseFromString(data)

    # Create response
    response = plugin.CodeGeneratorResponse()

    # Generate code
    generateCode(request,response)

    # Serialise response message
    output = response.SerializeToString()

    # Write to stdout
    sys.stdout.write(output)

