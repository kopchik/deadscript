#!/usr/bin/env python3

from functools import partial

from pratt import prefix, infix, infix_r, postfix, brackets, \
  symap, parse as pratt_parse
from useful.mstring import s
from log import Log
log = Log('ast')


#############
# TEMPLATES #
#############
class Node(list):
  fields = []

  def __init__(self, *args):
    if self.fields and len(args) != len(self.fields):
      raise Exception("Number of arguments mismatch defined fields")
    super().__init__(args)

  def __getattr__(self, name):
    assert name in self.fields, "Unknown field %s" % name
    idx = self.fields.index(name)
    return self[idx]

  def __setattr__(self, name, value):
    idx = self.fields.index(name)
    self[idx] = value

  def __dir__(self):
    return self.fields

  def __repr__(self):
    cls = self.__class__.__name__
    args = ", ".join("%s=%s"%(name, getattr(self,name)) for name in self.fields)
    return "%s(%s)" % (cls, args)


class Leaf:
  def __init__(self, value):
    assert not hasattr(self, 'fields'), "Leaf cannot have fields attribute"
    self.value = value
    super().__init__()

  def __repr__(self):
    cls = self.__class__.__name__
    return "%s:%s" % (cls, self.value)

  def __iter__(self):
    return iter([])

  def nud(self):
    return self


class Unary(Node):
  fields = ['value']


class Binary(Node):
  fields = ['left', 'right']


###########
# SPECIAL #
###########

class Id(Leaf):
  def __str__(self):
    return self.value


##############
# Data types #
##############

class Block(Node):
  def __repr__(self):
    return "%s(%s)" % (self.__class__.__name__, super().__repr__())
  __str__ = __repr__

  def nud(self):
    return self


class Str(Leaf): pass
class ShellCmd(Leaf):  pass
class RegEx(Leaf):  pass
class Int(Leaf):  pass


#########
# UNARY #
#########

@prefix('-', 100)
class Minus(Unary):
  pass

@prefix('+', 100)
class Plus(Unary):
  pass

@prefix('p', 0)
class Print(Unary):
  pass

# @prefix('->', 2)
# class Lambda0(Unary):
#   pass

@postfix('!', 3)
class CALL(Unary):
  pass


##########
# BINARY #
##########

@infix('+', 10)
class Add(Binary):
  pass

@infix('-', 10)
class Sub(Binary):
  pass

@infix_r('^', 30)
class Pow(Binary):
  pass

@infix_r('=', 1)
class Eq(Binary): pass

@infix('=~', 3)
class RegMatch(Binary): pass

@infix('->', 2)
class Lambda(Binary):
  fields = ['args', 'body']

@brackets('(',')')
class Parens(Unary):
  pass

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
  for i,n in enumerate(tree):
      if isinstance(n, Node):
        n = rewrite(n, f, d+1, **kwargs)
      tree[i] = f(n, d, **kwargs)
  return tree


def add_blocks(node, depth):
  """Add blocks"""
  if isinstance(node, list):
    return Block(node)
  return node


def precedence(ast):
  nodes = []
  for e in ast:
    if isinstance(e, list) and e:
      expr = precedence(e)
      if isinstance(expr, list):
        expr = pratt_parse(expr)
      nodes.append(expr)
    else:
      nodes.append(e)
  return nodes


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


def parse_args(node, depth):
  if not isinstance(node, Lambda):
    return node
  argnames = node.args[0][0]  # TODO: why so many nested lists?
  args = [Var(name.value) for name in argnames]
  node.args = args
  return node


def parse(ast):
  ast = rewrite(ast, add_blocks)
  log.blocks("after block parser:\n", ast)
  ast = precedence(ast)
  log.pratt("after pratt parser:\n", ast)

  ast = rewrite(ast, parse_args)
  log.rewrite("after rewriting func args:\n", ast)

  return ast