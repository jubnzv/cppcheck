"""
cppcheckdata

This is a Python module that helps you access Cppcheck dump data.

License: No restrictions, use this as you need.
"""

import argparse
import json
import os
import sys

from xml.etree import ElementTree
from fnmatch import fnmatch

class Directive:
    """
    Directive class. Contains information about each preprocessor directive in the source code.

    Attributes:
        str      The directive line, with all C or C++ comments removed
        file     Name of (possibly included) file where directive is defined
        linenr   Line number in (possibly included) file where directive is defined

    To iterate through all directives use such code:
    @code
    data = cppcheckdata.parsedump(...)
    for cfg in data.configurations:
      for directive in cfg.directives:
        print(directive.str)
    @endcode
    """

    str = None
    file = None
    linenr = None
    column = 0

    def __init__(self, element):
        self.str = element.get('str')
        self.file = element.get('file')
        self.linenr = int(element.get('linenr'))


class ValueType:
    """
    ValueType class. Contains (promoted) type information for each node in the AST.
    """

    type = None
    sign = None
    bits = 0
    constness = 0
    pointer = 0
    typeScopeId = None
    typeScope = None
    originalTypeName = None

    def __init__(self, element):
        self.type = element.get('valueType-type')
        self.sign = element.get('valueType-sign')
        bits = element.get('valueType-bits')
        if bits:
            self.bits = int(bits)
        self.typeScopeId = element.get('valueType-typeScope')
        self.originalTypeName = element.get('valueType-originalTypeName')
        constness = element.get('valueType-constness')
        if constness:
            self.constness = int(constness)
        else:
            self.constness = 0
        pointer = element.get('valueType-pointer')
        if pointer:
            self.pointer = int(pointer)
        else:
            self.pointer = 0

    def setId(self, IdMap):
        self.typeScope = IdMap[self.typeScopeId]

    def isIntegral(self):
        return self.type in {'bool', 'char', 'short', 'int', 'long', 'long long'}

    def isFloat(self):
        return self.type in {'float', 'double', 'long double'}

    def isEnum(self):
        return self.typeScope and self.typeScope.type == "Enum"


class Token:
    """
    Token class. Contains information about each token in the source code.

    The CppcheckData.tokenlist is a list of Token items

    C++ class: http://cppcheck.net/devinfo/doxyoutput/classToken.html

    Attributes:
        str                Token string
        next               Next token in tokenlist. For last token, next is None.
        previous           Previous token in tokenlist. For first token, previous is None.
        link               Linked token in tokenlist. Each '(', '[' and '{' are linked to the
                           corresponding '}', ']' and ')'. For templates, the '<' is linked to
                           the corresponding '>'.
        scope              Scope information for this token. See the Scope class.
        isName             Is this token a symbol name
        isNumber           Is this token a number, for example 123, 12.34
        isInt              Is this token a int value such as 1234
        isFloat            Is this token a int value such as 12.34
        isString           Is this token a string literal such as "hello"
        strlen             string length for string literal
        isChar             Is this token a char literal such as 'x'
        isOp               Is this token a operator
        isArithmeticalOp   Is this token a arithmetic operator
        isAssignmentOp     Is this token a assignment operator
        isComparisonOp     Is this token a comparison operator
        isLogicalOp        Is this token a logical operator: && ||
        isUnsigned         Is this token a unsigned type
        isSigned           Is this token a signed type
        isExpandedMacro    Is this token a expanded macro token
        varId              varId for token, each variable has a unique non-zero id
        variable           Variable information for this token. See the Variable class.
        function           If this token points at a function call, this attribute has the Function
                           information. See the Function class.
        values             Possible values of token
        valueType          type information
        typeScope          type scope (token->type()->classScope)
        astParent          ast parent
        astOperand1        ast operand1
        astOperand2        ast operand2
        file               file name
        linenr             line number
        column             column

    To iterate through all tokens use such code:
    @code
    data = cppcheckdata.parsedump(...)
    for cfg in data.configurations:
      code = ''
      for token in cfg.tokenlist:
        code = code + token.str + ' '
      print(code)
    @endcode
    """

    Id = None
    str = None
    next = None
    previous = None
    linkId = None
    link = None
    scopeId = None
    scope = None
    isName = False
    isNumber = False
    isInt = False
    isFloat = False
    isString = False
    strlen = None
    isChar = False
    isOp = False
    isArithmeticalOp = False
    isAssignmentOp = False
    isComparisonOp = False
    isLogicalOp = False
    isUnsigned = False
    isSigned = False
    isExpandedMacro = False
    varId = None
    variableId = None
    variable = None
    functionId = None
    function = None
    valuesId = None
    values = None
    valueType = None

    typeScopeId = None
    typeScope = None

    astParentId = None
    astParent = None
    astOperand1Id = None
    astOperand1 = None
    astOperand2Id = None
    astOperand2 = None

    file = None
    linenr = None
    column = None

    def __init__(self, element):
        self.Id = element.get('id')
        self.str = element.get('str')
        self.next = None
        self.previous = None
        self.scopeId = element.get('scope')
        self.scope = None
        type = element.get('type')
        if type == 'name':
            self.isName = True
            if element.get('isUnsigned'):
                self.isUnsigned = True
            if element.get('isSigned'):
                self.isSigned = True
        elif type == 'number':
            self.isNumber = True
            if element.get('isInt'):
                self.isInt = True
            elif element.get('isFloat'):
                self.isFloat = True
        elif type == 'string':
            self.isString = True
            self.strlen = int(element.get('strlen'))
        elif type == 'char':
            self.isChar = True
        elif type == 'op':
            self.isOp = True
            if element.get('isArithmeticalOp'):
                self.isArithmeticalOp = True
            elif element.get('isAssignmentOp'):
                self.isAssignmentOp = True
            elif element.get('isComparisonOp'):
                self.isComparisonOp = True
            elif element.get('isLogicalOp'):
                self.isLogicalOp = True
        if element.get('isExpandedMacro'):
            self.isExpandedMacro = True
        self.linkId = element.get('link')
        self.link = None
        if element.get('varId'):
            self.varId = int(element.get('varId'))
        self.variableId = element.get('variable')
        self.variable = None
        self.functionId = element.get('function')
        self.function = None
        self.valuesId = element.get('values')
        self.values = None
        if element.get('valueType-type'):
            self.valueType = ValueType(element)
        else:
            self.valueType = None
        self.typeScopeId = element.get('type-scope')
        self.typeScope = None
        self.astParentId = element.get('astParent')
        self.astParent = None
        self.astOperand1Id = element.get('astOperand1')
        self.astOperand1 = None
        self.astOperand2Id = element.get('astOperand2')
        self.astOperand2 = None
        self.file = element.get('file')
        self.linenr = int(element.get('linenr'))
        self.column = int(element.get('column'))

    def setId(self, IdMap):
        self.scope = IdMap[self.scopeId]
        self.link = IdMap[self.linkId]
        self.variable = IdMap[self.variableId]
        self.function = IdMap[self.functionId]
        self.values = IdMap[self.valuesId]
        self.typeScope = IdMap[self.typeScopeId]
        self.astParent = IdMap[self.astParentId]
        self.astOperand1 = IdMap[self.astOperand1Id]
        self.astOperand2 = IdMap[self.astOperand2Id]
        if self.valueType:
            self.valueType.setId(IdMap)

    def getValue(self, v):
        """
        Get value if it exists
        Returns None if it doesn't exist
        """

        if not self.values:
            return None
        for value in self.values:
            if value.intvalue == v:
                return value
        return None


class Scope:
    """
    Scope. Information about global scope, function scopes, class scopes, inner scopes, etc.
    C++ class: http://cppcheck.net/devinfo/doxyoutput/classScope.html

    Attributes
        bodyStart      The { Token for this scope
        bodyEnd        The } Token for this scope
        className      Name of this scope.
                       For a function scope, this is the function name;
                       For a class scope, this is the class name.
        function       If this scope belongs at a function call, this attribute
                       has the Function information. See the Function class.
        type           Type of scope: Global, Function, Class, If, While
    """

    Id = None
    bodyStartId = None
    bodyStart = None
    bodyEndId = None
    bodyEnd = None
    className = None
    functionId = None
    function = None
    nestedInId = None
    nestedIn = None
    type = None
    isExecutable = None

    def __init__(self, element):
        self.Id = element.get('id')
        self.className = element.get('className')
        self.functionId = element.get('function')
        self.function = None
        self.bodyStartId = element.get('bodyStart')
        self.bodyStart = None
        self.bodyEndId = element.get('bodyEnd')
        self.bodyEnd = None
        self.nestedInId = element.get('nestedIn')
        self.nestedIn = None
        self.type = element.get('type')
        self.isExecutable = (self.type in ('Function', 'If', 'Else', 'For', 'While', 'Do',
                                           'Switch', 'Try', 'Catch', 'Unconditional', 'Lambda'))

    def setId(self, IdMap):
        self.bodyStart = IdMap[self.bodyStartId]
        self.bodyEnd = IdMap[self.bodyEndId]
        self.nestedIn = IdMap[self.nestedInId]
        self.function = IdMap[self.functionId]


class Function:
    """
    Information about a function
    C++ class:
    http://cppcheck.net/devinfo/doxyoutput/classFunction.html

    Attributes
        argument                Argument list
        tokenDef                Token in function definition
        isVirtual               Is this function is virtual
        isImplicitlyVirtual     Is this function is virtual this in the base classes
        isStatic                Is this function is static
    """

    Id = None
    argument = None
    argumentId = None
    tokenDef = None
    tokenDefId = None
    name = None
    type = None
    isVirtual = None
    isImplicitlyVirtual = None
    isStatic = None

    def __init__(self, element):
        self.Id = element.get('id')
        self.tokenDefId = element.get('tokenDef')
        self.name = element.get('name')
        self.type = element.get('type')
        isVirtual = element.get('isVirtual')
        self.isVirtual = (isVirtual and isVirtual == 'true')
        isImplicitlyVirtual = element.get('isImplicitlyVirtual')
        self.isImplicitlyVirtual = (isImplicitlyVirtual and isImplicitlyVirtual == 'true')
        isStatic = element.get('isStatic')
        self.isStatic = (isStatic and isStatic == 'true')

        self.argument = {}
        self.argumentId = {}

    def setId(self, IdMap):
        for argnr, argid in self.argumentId.items():
            self.argument[argnr] = IdMap[argid]
        self.tokenDef = IdMap[self.tokenDefId]


class Variable:
    """
    Information about a variable
    C++ class:
    http://cppcheck.net/devinfo/doxyoutput/classVariable.html

    Attributes:
        nameToken       Name token in variable declaration
        typeStartToken  Start token of variable declaration
        typeEndToken    End token of variable declaration
        access          Global/Local/Namespace/Public/Protected/Public/Throw/Argument
        scope           Variable scope
        isArgument      Is this variable a function argument?
        isArray         Is this variable an array?
        isClass         Is this variable a class or struct?
        isConst         Is this variable a const variable?
        isGlobal        Is this variable a global variable?
        isExtern        Is this variable an extern variable?
        isLocal         Is this variable a local variable?
        isPointer       Is this variable a pointer
        isReference     Is this variable a reference
        isStatic        Is this variable static?
        constness       Variable constness (same encoding as ValueType::constness)
    """

    Id = None
    nameTokenId = None
    nameToken = None
    typeStartTokenId = None
    typeStartToken = None
    typeEndTokenId = None
    typeEndToken = None
    access = None
    scopeId = None
    scope = None
    isArgument = False
    isArray = False
    isClass = False
    isConst = False
    isExtern = False
    isGlobal = False
    isLocal = False
    isPointer = False
    isReference = False
    isStatic = False
    constness = 0

    def __init__(self, element):
        self.Id = element.get('id')
        self.nameTokenId = element.get('nameToken')
        self.nameToken = None
        self.typeStartTokenId = element.get('typeStartToken')
        self.typeStartToken = None
        self.typeEndTokenId = element.get('typeEndToken')
        self.typeEndToken = None
        self.access = element.get('access')
        self.scopeId = element.get('scope')
        self.scope = None
        self.isArgument = element.get('isArgument') == 'true'
        self.isArray = element.get('isArray') == 'true'
        self.isClass = element.get('isClass') == 'true'
        self.isConst = element.get('isConst') == 'true'
        self.isGlobal = element.get('access') == 'Global'
        self.isExtern = element.get('isExtern') == 'true'
        self.isLocal = element.get('isLocal') == 'true'
        self.isPointer = element.get('isPointer') == 'true'
        self.isReference = element.get('isReference') == 'true'
        self.isStatic = element.get('isStatic') == 'true'
        self.constness = element.get('constness')
        if self.constness:
            self.constness = int(self.constness)

    def setId(self, IdMap):
        self.nameToken = IdMap[self.nameTokenId]
        self.typeStartToken = IdMap[self.typeStartTokenId]
        self.typeEndToken = IdMap[self.typeEndTokenId]
        self.scope = IdMap[self.scopeId]


class Value:
    """
    Value class

    Attributes:
        intvalue         integer value
        tokvalue         token value
        floatvalue       float value
        containerSize    container size
        condition        condition where this Value comes from
        valueKind        'known' or 'possible'
        inconclusive     Is value inconclusive?
    """

    intvalue = None
    tokvalue = None
    floatvalue = None
    containerSize = None
    condition = None
    valueKind = None
    inconclusive = False

    def isKnown(self):
        return self.valueKind and self.valueKind == 'known'

    def isPossible(self):
        return self.valueKind and self.valueKind == 'possible'

    def __init__(self, element):
        self.intvalue = element.get('intvalue')
        if self.intvalue:
            self.intvalue = int(self.intvalue)
        self.tokvalue = element.get('tokvalue')
        self.floatvalue = element.get('floatvalue')
        self.containerSize = element.get('container-size')
        self.condition = element.get('condition-line')
        if self.condition:
            self.condition = int(self.condition)
        if element.get('known'):
            self.valueKind = 'known'
        elif element.get('possible'):
            self.valueKind = 'possible'
        if element.get('inconclusive'):
            self.inconclusive = True


class ValueFlow:
    """
    ValueFlow::Value class
    Each possible value has a ValueFlow::Value item.
    Each ValueFlow::Value either has a intvalue or tokvalue
    C++ class:
    http://cppcheck.net/devinfo/doxyoutput/classValueFlow_1_1Value.html

    Attributes:
        values    Possible values
    """

    Id = None
    values = None

    def __init__(self, element):
        self.Id = element.get('id')
        self.values = []


class Suppression:
    """
    Suppression class
    This class contains a suppression entry to suppress a warning.

    Attributes
      errorId     The id string of the error to suppress, can be a wildcard
      fileName    The name of the file to suppress warnings for, can include wildcards
      lineNumber  The number of the line to suppress warnings from, can be 0 to represent any line
      symbolName  The name of the symbol to match warnings for, can include wildcards
    """

    errorId = None
    fileName = None
    lineNumber = None
    symbolName = None

    def __init__(self, element):
        self.errorId = element.get('errorId')
        self.fileName = element.get('fileName')
        self.lineNumber = element.get('lineNumber')
        self.symbolName = element.get('symbolName')

    def isMatch(self, file, line, message, errorId):
        if ((self.fileName is None or fnmatch(file, self.fileName))
                and (self.lineNumber is None or line == self.lineNumber)
                and (self.symbolName is None or fnmatch(message, '*'+self.symbolName+'*'))
                and fnmatch(errorId, self.errorId)):
            return True
        else:
            return False


class Configuration:
    """
    Configuration class
    This class contains the directives, tokens, scopes, functions,
    variables, value flows, and suppressions for one configuration.

    Attributes:
        name          Name of the configuration, "" for default
        directives    List of Directive items
        tokenlist     List of Token items
        scopes        List of Scope items
        functions     List of Function items
        variables     List of Variable items
        valueflow     List of ValueFlow values
        standards     List of Standards values
    """

    name = ''
    directives = []
    tokenlist = []
    scopes = []
    functions = []
    variables = []
    valueflow = []
    standards = []

    def __init__(self, name):
        self.name = name
        self.directives = []
        self.tokenlist = []
        self.scopes = []
        self.functions = []
        self.variables = []
        self.valueflow = []
        self.standards = []

    def set_tokens_links(self):
        """Set next/previous links between tokens."""
        prev = None
        for token in self.tokenlist:
            token.previous = prev
            if prev:
                prev.next = token
            prev = token

    def set_id_map(self, arguments):
        IdMap = {None: None, '0': None, '00000000': None, '0000000000000000': None}
        for token in self.tokenlist:
            IdMap[token.Id] = token
        for scope in self.scopes:
            IdMap[scope.Id] = scope
        for function in self.functions:
            IdMap[function.Id] = function
        for variable in self.variables:
            IdMap[variable.Id] = variable
        for variable in arguments:
            IdMap[variable.Id] = variable
        for values in self.valueflow:
            IdMap[values.Id] = values.values
        for token in self.tokenlist:
            token.setId(IdMap)
        for scope in self.scopes:
            scope.setId(IdMap)
        for function in self.functions:
            function.setId(IdMap)
        for variable in self.variables:
            variable.setId(IdMap)
        for variable in arguments:
            variable.setId(IdMap)

    def setIdMap(self, functions_arguments):
        """Set relationships between objects stored in this configuration.
        :param functions_arguments: List of Variable objects which are function arguments
        """
        self.set_tokens_links()
        self.set_id_map(functions_arguments)


class Platform:
    """
    Platform class
    This class contains type sizes

    Attributes:
        name          Name of the platform
        char_bit      CHAR_BIT value
        short_bit     SHORT_BIT value
        int_bit       INT_BIT value
        long_bit      LONG_BIT value
        long_long_bit LONG_LONG_BIT value
        pointer_bit   POINTER_BIT value
    """

    name = ''
    char_bit = 0
    short_bit = 0
    int_bit = 0
    long_bit = 0
    long_long_bit = 0
    pointer_bit = 0

    def __init__(self, platformnode):
        self.name = platformnode.get('name')
        self.char_bit = int(platformnode.get('char_bit'))
        self.short_bit = int(platformnode.get('short_bit'))
        self.int_bit = int(platformnode.get('int_bit'))
        self.long_bit = int(platformnode.get('long_bit'))
        self.long_long_bit = int(platformnode.get('long_long_bit'))
        self.pointer_bit = int(platformnode.get('pointer_bit'))


class Standards:
    """
    Standards class
    This class contains versions of standards that were used for the cppcheck

    Attributes:
        c            C Standard used
        cpp          C++ Standard used
        posix        If Posix was used
    """

    def __init__(self, standardsnode):
        self.c = standardsnode.find("c").get("version")
        self.cpp = standardsnode.find("cpp").get("version")
        self.posix = standardsnode.find("posix") is not None


class CppcheckData:
    """
    Class that makes cppcheck dump data available
    Contains a list of Configuration instances

    Attributes:
        filename          Path to Cppcheck dump file
        rawTokens         List of rawToken elements
        suppressions      List of Suppressions

    To iterate through all configurations use such code:
    @code
    data = cppcheckdata.parsedump(...)
    for cfg in data.configurations:
        print('cfg: ' + cfg.name)
    @endcode

    To iterate through all tokens in each configuration use such code:
    @code
    data = cppcheckdata.parsedump(...)
    for cfg in data.configurations:
        print('cfg: ' + cfg.name)
        code = ''
            for token in cfg.tokenlist:
                code = code + token.str + ' '
        print('    ' + code)
    @endcode

    To iterate through all scopes (functions, types, etc) use such code:
    @code
    data = cppcheckdata.parsedump(...)
    for cfg in data.configurations:
        print('cfg: ' + cfg.name)
        for scope in cfg.scopes:
            print('    type:' + scope.type + ' name:' + scope.className)
    @endcode
    """

    rawTokens = []
    platform = None
    suppressions = []

    def __init__(self, filename):
        """
        :param filename: Path to Cppcheck dump file
        """
        self.filename = filename

        files = []  # source files for elements occurred in this configuration
        platform_done = False
        rawtokens_done = False
        suppressions_done = False

        # Parse general configuration options from <dumps> node
        # We intentionally don't clean node resources here because we
        # want to serialize in memory only small part of the XML tree.
        for event, node in ElementTree.iterparse(self.filename, events=('start', 'end')):
            if platform_done and rawtokens_done and suppressions_done:
                break
            if node.tag == 'platform' and event == 'start':
                self.platform = Platform(node)
                platform_done = True
            elif node.tag == 'rawtokens' and event == 'end':
                for rawtokens_node in node:
                    if rawtokens_node.tag == 'file':
                        files.append(rawtokens_node.get('name'))
                    elif rawtokens_node.tag == 'tok':
                        tok = Token(rawtokens_node)
                        tok.file = files[int(rawtokens_node.get('fileIndex'))]
                        self.rawTokens.append(tok)
                rawtokens_done = True
            elif node.tag == 'suppressions' and event == 'end':
                for suppressions_node in node:
                    self.suppressions.append(Suppression(suppressions_node))
                suppressions_done = True

        # Set links between rawTokens.
        for i in range(len(self.rawTokens)-1):
            self.rawTokens[i+1].previous = self.rawTokens[i]
            self.rawTokens[i].next = self.rawTokens[i+1]

    @property
    def configurations(self):
        """
        Return the list of all available Configuration objects.
        """
        return list(self.iterconfigurations())

    def iterconfigurations(self):
        """
        Create and return iterator for the available Configuration objects.
        The iterator loops over all Configurations in the dump file tree, in document order.
        """
        cfg = None
        cfg_arguments = []  # function arguments for Configuration node initialization
        cfg_function = None
        cfg_valueflow = None

        # Scopes contains <varlist> with all occurred variables. Some of them
        # appearaed in <variables> node for this configuration.
        # Others are arguments of functions.
        # They have similar tag <var> but doesn't contain any attributes. So we
        # set set a special state when iterate <varlist> node to prevent
        # overriding of cfg.variables list with empty values.
        iter_varlist = False

        # Use iterable objects to traverse XML tree for dump files incrementally.
        # Iterative approach is required to avoid large memory consumption.
        # Calling .clear() is necessary to let the element be garbage collected.
        for event, node in ElementTree.iterparse(self.filename, events=('start', 'end')):
            # Serialize new configuration node
            if node.tag == 'dump':
                if event == 'start':
                    cfg = Configuration(node.get('cfg'))
                    continue
                elif event == 'end':
                    cfg.setIdMap(cfg_arguments)
                    yield cfg
                    cfg = None
                    cfg_arguments = []

            # Parse nested elemenets of configuration node
            elif node.tag == "standards" and event == 'start':
                continue
            elif node.tag == "standards" and event == 'end':
                cfg.standards = Standards(node)

            # Parse directives list
            elif node.tag == 'directive' and event == 'start':
                cfg.directives.append(Directive(node))

            # Parse tokens
            elif node.tag == 'tokenlist' and event == 'start':
                continue
            elif node.tag == 'token' and event == 'start':
                cfg.tokenlist.append(Token(node))

            # Parse scopes
            elif node.tag == 'scopes' and event == 'start':
                continue
            elif node.tag == 'scope' and event == 'start':
                cfg.scopes.append(Scope(node))
            elif node.tag == 'varlist':
                if event == 'start':
                    iter_varlist = True
                elif event == 'end':
                    iter_varlist = False

            # Parse functions
            elif node.tag == 'functionList' and event == 'start':
                continue
            elif node.tag == 'function':
                if event == 'start':
                    cfg_function = Function(node)
                    continue
                elif event == 'end':
                    cfg.functions.append(cfg_function)
                    cfg_function = None

            # Parse function arguments
            elif node.tag == 'arg' and event == 'start':
                arg_nr = int(node.get('nr'))
                arg_variable_id = node.get('variable')
                cfg_function.argumentId[arg_nr] = arg_variable_id

            # Parse variables
            elif node.tag == 'var' and event == 'start':
                var = Variable(node)
                if var.nameTokenId:
                    cfg.variables.append(var)
                elif not iter_varlist:
                    cfg_arguments.append(var)

            # Parse valueflows (list of values)
            elif node.tag == 'valueflow' and event == 'start':
                continue
            elif node.tag == 'values':
                if event == 'start':
                    cfg_valueflow = ValueFlow(node)
                    continue
                elif event == 'end':
                    cfg.valueflow.append(cfg_valueflow)
                    cfg_valueflow = None

            # Parse values
            elif node.tag == 'value' and event == 'start':
                cfg_valueflow.values.append(Value(node))

            # Remove links to the sibling nodes
            node.clear()


# Get function arguments
def getArgumentsRecursive(tok, arguments):
    if tok is None:
        return
    if tok.str == ',':
        getArgumentsRecursive(tok.astOperand1, arguments)
        getArgumentsRecursive(tok.astOperand2, arguments)
    else:
        arguments.append(tok)


def getArguments(ftok):
    if (not ftok.isName) or (ftok.next is None) or ftok.next.str != '(':
        return None
    args = []
    getArgumentsRecursive(ftok.next.astOperand2, args)
    return args


def parsedump(filename):
    """
    parse a cppcheck dump file
    """
    return CppcheckData(filename)


def astIsFloat(token):
    """
    Check if type of ast node is float/double
    """

    if not token:
        return False
    if token.str == '.':
        return astIsFloat(token.astOperand2)
    if token.str in '+-*/%':
        return astIsFloat(token.astOperand1) or astIsFloat(token.astOperand2)
    if not token.variable:
        # float literal?
        if token.str[0].isdigit():
            for c in token.str:
                if c == 'f' or c == '.' or c == 'E':
                    return True
        return False
    typeToken = token.variable.typeStartToken
    endToken = token.variable.typeEndToken
    while typeToken != endToken:
        if typeToken.str == 'float' or typeToken.str == 'double':
            return True
        typeToken = typeToken.next
    if typeToken.str == 'float' or typeToken.str == 'double':
        return True
    return False


class CppCheckFormatter(argparse.HelpFormatter):
    """
    Properly formats multiline argument helps
    """
    def _split_lines(self, text, width):
        # this is the RawTextHelpFormatter._split_lines
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)


def ArgumentParser():
    """
    Returns an argparse argument parser with an already-added
    argument definition for -t/--template
    """
    parser = argparse.ArgumentParser(formatter_class=CppCheckFormatter)
    parser.add_argument('-t', '--template', metavar='<text>',
                        default='{callstack}: ({severity}) {message}',
                        help="R|Format the error messages. E.g.\n"
                        "'{file}:{line},{severity},{id},{message}' or\n"
                        "'{file}({line}):({severity}) {message}' or\n"
                        "'{callstack} {message}'\n"
                        "Pre-defined templates: gcc, vs, edit")
    parser.add_argument("dumpfile", nargs='*',
                        help="Path of dump files from cppcheck.")
    parser.add_argument("--cli",
                        help="Addon is executed from Cppcheck",
                        action="store_true")
    parser.add_argument("-q", "--quiet",
                        help='do not print "Checking ..." lines',
                        action="store_true")
    return parser


def simpleMatch(token, pattern):
    for p in pattern.split(' '):
        if not token or token.str != p:
            return False
        token = token.next
    return True


def reportError(location, severity, message, addon, errorId, extra=''):
    if '--cli' in sys.argv:
        msg = { 'file': location.file,
                'linenr': location.linenr,
                'column': location.column,
                'severity': severity,
                'message': message,
                'addon': addon,
                'errorId': errorId,
                'extra': extra}
        sys.stdout.write(json.dumps(msg) + '\n')
    else:
        loc = '[%s:%i]' % (location.file, location.linenr)
        if len(extra) > 0:
            message += ' (' + extra + ')'
        sys.stderr.write('%s (%s) %s [%s-%s]\n' % (loc, severity, message, addon, errorId))
