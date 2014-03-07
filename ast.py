#!/usr/bin/env python3

from pratt import prefix, infix, infix_r, postfix, brackets, \
  subscript, action, symap, parse as pratt_parse
from log import Log
log = Log('ast')


#############
# TEMPLATES #
#############
class Node(list):
  """ Base class for the most
      syntax elements. It is a subclass of list
      to support iteration over its elements.
      It also supports access to the elements
      through attributes. Names of attributes to
      be specified in class.fields.
  """
  fields = []

  def __init__(self, *args):
    if self.fields and len(args) != len(self.fields):
      raise Exception("Number of arguments mismatch defined fields")
    super().__init__(args)

  def __getattr__(self, name):
    if name not in self.fields:
      raise AttributeError("Unknown attribute %s for %s (%s)" % (name, type(self), self.fields))
    idx = self.fields.index(name)
    return self[idx]

  def __setattr__(self, name, value):
    if name not in self.fields:
      raise AttributeError("Unknown attribute %s for %s (%s)" % (name, type(self), self.fields))
    idx = self.fields.index(name)
    self[idx] = value

  def __dir__(self):
    return self.fields

  def __repr__(self):
    cls = self.__class__.__name__
    if self.fields:
      args = ", ".join("%s=%s"%(name, getattr(self,name)) for name in self.fields)
    else:
      args = ", ".join(map(str,self))
    return "%s(%s)" % (cls, args)


class Leaf:
  """ Base class for AST elements that do not
      support iteration over them.
  """
  lbp = 0
  def __init__(self, value):
    assert not hasattr(self, 'fields'), \
      "Leaf subclass cannot have fields attribute (it's not Node)"
    self.value = value
    super().__init__()

  def __repr__(self):
    cls = self.__class__.__name__
    return "%s:%s" % (cls, self.value)

  def nud(self):
    return self


class Unary(Node):
  fields = ['arg']


class Binary(Node):
  fields = ['left', 'right']


class Expr(Node):
  """ It's an expression.
  """
  def __repr__(self):
    return "Expr(%s)" % ", ".join(str(s) for s in self)


class Block(Node):
  """ It's block of one or more separate expressions.
  """
  # lbp = 1
  def nud(self):
    return self

  # def led(self, left):
  #   print("LEFT:", left)
  #   return self

  def __repr__(self):
    return "Block!(%s)" % ", ".join(str(t) for t in self)
  __str__ = __repr__


class Comment(Leaf): pass
##############
# Data Types #
##############

class Str(Leaf):  pass
class ShellCmd(Leaf):  pass
class RegEx(Leaf):  pass
class Int(Leaf):  pass
class Id(Leaf): pass


###########
# SPECIAL #
###########

@prefix('p', 0)
class Print(Unary): pass

@action('_')
class AlwaysTrue(Leaf): pass


#########
# UNARY #
#########

@prefix('-', 100)
class Minus(Unary): pass

@prefix('+', 100)
class Plus(Unary): pass

@prefix('match', 1)
class Match(Node): pass

@prefix('->', 2)
class Lambda0(Unary): pass

@postfix('!', 3)
class Call0(Unary): pass


##########
# BINARY #
##########

@infix('+', 10)
class Add(Binary): pass

@infix('-', 10)
class Sub(Binary): pass

@infix('*', 20)
class Mul(Binary): pass

@infix_r('^', 30)
class Pow(Binary): pass

@infix_r('=', 1)
class Assign(Binary): pass

@infix_r('==', 2)
class Eq(Binary): pass

@infix('<', 2)
class Less(Binary): pass

@infix('>', 2)
class More(Binary): pass

@infix('=>', 1)
class IfThen(Binary):
  fields = ['iff', 'then']

@infix('=~', 3)
class RegMatch(Binary): pass

@infix('->', 2)
class Lambda(Binary):
  fields = ['args', 'body']

@brackets('(',')')
class Parens(Unary): pass

@brackets('[',']')
class Brackets(Unary): pass

@subscript('[', ']', -1000)
class Subscript(Binary): pass

@infix(',', 1)
class Comma(Node):
  fields = None
  """ Two and more commas in a row
      will be merged into one.
  """
  def __init__(self, left, right):
    values = []
    if isinstance(left, Comma):
      values += left + [right]
    else:
      values = [left, right]
    super().__init__(values)

  def __repr__(self):
    cls = self.__class__.__name__
    return "(%s %s)" % (cls, list(self))


class Var(Leaf):
  def __str__(self):
    return "%s(\"%s\")" % (self.__class__.__name__, self.value)



#######################
# AST TRANSFORMATIONS #
#######################

def rewrite(tree, f, d=0, **kwargs):
  if d==0: tree = f(tree, d, **kwargs)  # TODO: is this a dirty hack?
  for i,n in enumerate(tree):
      if isinstance(n, Node):
        n = rewrite(n, f, d+1, **kwargs)
      tree[i] = f(n, d, **kwargs)
  return tree


def precedence(node, depth):
  if not isinstance(node, Expr):
    return node
  try:
    return pratt_parse(node)
  except Exception as err:
    raise Exception("cannot process expression %s (%s)" % (node, err)) from Exception

def func_args(node, depth):
  """ Parses function arguments. """
  if not isinstance(node, Lambda):
    return node
  argnames = node.args[0][0]  # TODO: why so many nested lists?
  args = [Var(name.value) for name in argnames]
  node.args = args
  return node


def pretty_print(ast, lvl=0):
  prefix = " "*lvl
  for e in ast:
    if isinstance(e, Node):
      print(prefix, type(e).__name__)
      pretty_print(e, lvl+1)
    else:
      print(prefix, e)
  if lvl == 0:
    print()


def parse(ast):
  ast = rewrite(ast, precedence)
  log.pratt("after pratt parser:\n", ast)

  ast = rewrite(ast, func_args)
  log.rewrite("after parsing functions' args:\n", ast)

  return ast