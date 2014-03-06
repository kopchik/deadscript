from ast import Node, Unary, Binary, Leaf, rewrite
from collections import OrderedDict
from frame import Frame
from log import Log
import ast

from subprocess import check_output
import shlex
import re

log = Log("interpreter")
astMap = OrderedDict()


class replaces:
  """ Decorator to substitute nodes in AST. """
  def __init__(self, oldCls):
    self.oldCls = oldCls

  def __call__(self, newCls):
    astMap[self.oldCls] = newCls
    return newCls


def replace_nodes(node, depth):
    for oldCls, newCls in astMap.items():
      if isinstance(node, oldCls):
        log.replace("replacing %s (%s)" % (node, type(node)))
        if isinstance(node, Leaf):
          return newCls(node.value)
        return newCls(*node)
    return node


class Value(Leaf):
  def run(self, frame):
    return self


class BinOp(Binary):
  def run(self, frame):
    opname = self.__class__.__name__
    left = self.left.run(frame)
    right = self.right.run(frame)
    assert type(left) == type(right), \
      "left and right values should have the same type," \
      "got %s and %s insted" % (left, right)
    assert hasattr(left, opname), \
      "%s does not support %s operation" % (left, opname)
    return getattr(left, opname)(right)


@replaces(ast.Lambda)
class Func(Node):
  fields = ['args', 'body']
  def run(self, frame):
    return self.body.run(frame)


@replaces(ast.Block)
class Block(Node):
  def run(self, frame):
    r = None
    for e in self:
      r = e.run(frame)
    return r


#TODO: it's an unary operator
@replaces(ast.Print)
class Print(Node):
  fields = ['arg']
  def run(self, frame):
    r = self.arg.run(frame)
    print(r.to_string(frame))
    return self.arg


class RegEx(Leaf):
  def match(self, string, frame):
    expr = self.value[1:-1]
    m = re.match(expr, str(string))
    if not m:
      return False
    groupdict = m.groupdict()
    if groupdict:
      frame.update(groupdict)
    group = m.group()
    if group:
      return group
    return True


class RegMatch(Binary):
  def run(self, frame):
    return self.left.match(self.right, frame)


@replaces(ast.Int)
class Int(Value):
  def __init__(self, value):
    self.value = int(value)

  def __repr__(self):
    return "\"%s\"" % self.value

  def __str__(self):
    return str(self.value)

  def __add__(self, right):
    return Int(self.value + right.value)

  def to_string(self, frame):
    return str(self)

  def to_int(self):
    return self.value

  def Sub(self, other):
    return Int(self.value-other.value)


class Str(ast.Leaf):
  def __str__(self):
    return self.value[1:-1]

  def to_string(self, frame):
    replace = {r'\n': '\n', r'\t': '\t'}
    string = self.value.strip('"')
    varnames = re.findall("\{([a-zA-Z\.]+)\}", string, re.M)
    for name in varnames:
        value = Var(name).run(frame).to_string(frame)
        string = string.replace("{%s}" % name, value)
    for k,v in replace.items():
      string = string.replace(k, v)
    return string

  def run(self, frame):
    return self


class ShellCmd(Str):
  def run(self, frame):
    cmd = super().run(frame)
    cmd = cmd.strip('`')
    raw = check_output(shlex.split(cmd))
    return raw.decode()


class Array(Node):
  def to_string(self, frame):
    #TODO: recursively call to_string
    # print(type(self.value[0]))
    return '[' + ", ".join(x.to_string(frame) for x in self) + ']'

  def Subscript(self, idx):
    return self[idx.to_int()]

  def run(self, frame):
    return self


class Var(Leaf):
  def __str__(self):
    return str(self.value)

  def run(self, frame):
    return frame[self.value]


class Add(Binary):
  def run(self, frame):
    left = self.left.run(frame)
    right = self.right.run(frame)
    return left + right


@replaces(ast.Eq)
class Assign(BinOp):
  def run(self, frame):
    value = self.right.run(frame)
    frame[str(self.left)] = value
    return value


@replaces(ast.Parens)
class Parens(Unary):
  def run(self, frame):
    return self.value.run(frame)


@replaces(ast.Sub)
class Sub(BinOp):
  pass


@replaces(ast.Subscript)
class Subscript(BinOp):
  pass

def replace_nodes2(node, depth):
  if isinstance(node, ast.Str):
    return Str(node.value)
  if isinstance(node, ast.Add):
    return Add(node.left, node.right)
  if isinstance(node, ast.Id):
    return Var(node.value)
  if isinstance(node, ast.ShellCmd):
    return ShellCmd(node.value)
  if isinstance(node, ast.RegEx):
    return RegEx(node.value)
  if isinstance(node, ast.RegMatch):
    if isinstance(node.left, (Str, ast.Str)):
      return RegMatch(node.right, node.left)
    return RegMatch(node.left, node.right)
  if isinstance(node, ast.Brackets):
    return Array(node.value)
  return node


def populate_top_frame(node, depth, frame):
  if depth == 0:
    print("!", node)
  if depth == 0 and isinstance(node, Assign):
    key   = str(node.left)
    value = node.right
    frame[key] = value
  return node


def run(ast, args=[]):
  frame = Frame()
  ast = rewrite(ast, replace_nodes)
  ast = rewrite(ast, replace_nodes2)
  log.final_ast("the final AST is:\n", ast)

  ast = rewrite(ast, populate_top_frame, frame=frame)
  log.topframe("the top frame is\n", frame)

  if 'main' not in frame:
    print("no main function defined, exiting")
    return

  with frame as newframe:
    func = newframe['main']
    newframe['argc'] = Int(len(args))
    newframe['argv'] = Array(*map(Str,args))
    func.run(newframe)