#!/usr/bin/env python3

from pratt import prefix, infix, infix_r, postfix, brackets, \
  symap, parse as pratt_parse
# from useful.mstring import s
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
    assert name in self.fields, "Unknown field %s for %s" % (name, type(self))
    idx = self.fields.index(name)
    return self[idx]

  def __setattr__(self, name, value):
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
  def __init__(self, value):
    assert not hasattr(self, 'fields'), "Leaf cannot have fields attribute"
    self.value = value
    super().__init__()

  def __repr__(self):
    cls = self.__class__.__name__
    return "%s:%s" % (cls, self.value)

  def nud(self):
    return self


class Unary(Node):
  fields = ['value']


class Binary(Node):
  fields = ['left', 'right']


class Block(Node):
  def nud(self):
    return self

  def __repr__(self):
    return "Block!(%s)" % ", ".join(str(t) for t in self)
  __str__ = __repr__


class Expr(Node):
  def __repr__(self):
    return "Expr(%s)" % ", ".join(str(s) for s in self)


##############
# Data Types #
##############

class Str(Leaf): pass
class ShellCmd(Leaf):  pass
class RegEx(Leaf):  pass
class Int(Leaf):  pass

class Id(Leaf):
  def __str__(self):
    return self.value


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

@brackets('[',']')
class Brackets(Unary):
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


# def precedence(ast):
#   nodes = []
#   for e in ast:
#     if isinstance(e, Block) and e:
#       expr = precedence(e)
#       if isinstance(expr, Expr):
#         expr = pratt_parse(expr)
#       nodes.append(expr)
#     else:
#       nodes.append(e)
#   return nodes

def precedence(node, depth):
  if not isinstance(node, Expr):
    return node
  return pratt_parse(node)


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
  # ast = precedence(ast)
  ast = rewrite(ast, precedence)
  log.pratt("after pratt parser:\n", ast)

  ast = rewrite(ast, parse_args)
  log.rewrite("after rewriting func args:\n", ast)

  return ast