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
  def eval(self, frame):
    return self


@replaces(ast.Int)
class Int(Value):
  def __init__(self, value):
    self.value = int(value)

  def to_string(self, frame):
    return str(self.value)

  def to_int(self):
    return self.value

  def Add(self, right):
    return Int(self.value + right.value)

  def Eq(self, other):
    return Bool(self.value == other.value)

  def Less(self, other):
    return Bool(self.value < other.value)

  def More(self, other):
    return Bool(self.value > other.value)

  def Sub(self, other):
    return Int(self.value-other.value)

  def Mul(self, other):
    return Int(self.value*other.value)

  def Pow(self, other):
    return Int(self.value**other.value)


@replaces(ast.Str)
class Str(Value):
  def to_string(self, frame):
    string = self.value
    replace = {r'\n': '\n', r'\t': '\t'}
    varnames = re.findall("\{([a-zA-Z\.]+)\}", string, re.M)
    for name in varnames:
        value = Var(name).eval(frame).to_string(frame)
        string = string.replace("{%s}" % name, value)
    for k,v in replace.items():
      string = string.replace(k, v)
    return string


@replaces(ast.ShellCmd)
class ShellCmd(Str):
  def eval(self, frame):
    cmd = super().eval(frame).to_string(frame)
    raw = check_output(shlex.split(cmd))
    return Str(raw.decode())


@replaces(ast.Brackets)
class Array(Value):
  def to_string(self, frame):
    #TODO: recursively call to_string
    return '[' + ", ".join(x.to_string(frame) for x in self) + ']'

  def Subscript(self, idx):
    return self[idx.to_int()]


class Bool(Value):
  def __bool__(self):
    return self.value

  def to_string(self, frame):
    return str(self.value)


@replaces(ast.RegEx)
class RegEx(Value):
  def RegMatch(self, string):
    m = re.match(self.value, string.to_string(frame))
    if not m:
      return Bool(False)
    groupdict = m.groupdict()
    if groupdict:
      frame.update(groupdict) # TODO: frame not provided in args
    group = m.group()
    if group:
      return Str(group)
    return Bool(True)


@replaces(ast.Id)
class Var(Leaf):
  def __str__(self):
    return str(self.value)

  def Assign(self, value, frame):
    # self.value actually holds the name
    frame[self.value] = value

  def eval(self, frame):
    try:
      return frame[self.value]
    except KeyError:
      raise Exception("unknown variable \"%s\"" % self.value)


class BinOp(Binary):
  same_type_operands = True
  def eval(self, frame):
    opname = self.__class__.__name__
    left = self.left.eval(frame)
    right = self.right.eval(frame)
    if self.same_type_operands and type(left) != type(right):
      raise Exception(
      "left and right values should have the same type," \
      "got %s and %s insted" % (left, right))
    assert hasattr(left, opname), \
      "%s (%s) does not support %s operation" % (left, type(left), opname)
    return getattr(left, opname)(right)


@replaces(ast.Lambda)
class Func(Node):
  fields = ['args', 'body']

  # def Assign(self, frame):
  #   return self

  def Call(self, frame):
    return self.body.eval(frame)

  def eval(self, frame):
    return self


@replaces(ast.Lambda0)
class Func0(Node):
  fields = ['body']

  def Call(self, frame):
    return self.body.eval(frame)

  def eval(self, frame):
    return self


@replaces(ast.Block)
class Block(Node):
  def eval(self, frame):
    r = None
    for e in self:
      r = e.eval(frame)
    return r


@replaces(ast.Print)
class Print(Unary):
  fields = ['arg']
  def eval(self, frame):
    r = self.arg.eval(frame)
    print(r.to_string(frame))
    return r

@replaces(ast.Assert)
class Assert(Unary):
  def eval(self, frame):
    r = self.arg.eval(frame)
    if not r:
      raise Exception("Assertion failed on %s" % self.arg)
    return r


@replaces(ast.RegMatch)
class RegMatch(BinOp):
  same_type_operands = False
  def __init__(self, left, right):
    if isinstance(left, (Str, ast.Str)):
      left, right = right, left
    super().__init__(left, right)


@replaces(ast.Add)
class Add(BinOp): pass

@replaces(ast.Mul)
class Mul(BinOp): pass

@replaces(ast.Assign)
class Assign(BinOp):
  def eval(self, frame):
    value = self.right.eval(frame)
    # TODO: lvalue should be a valid ID
    self.left.Assign(value, frame)
    return value


@replaces(ast.Eq)
class Eq(BinOp): pass

@replaces(ast.Less)
class Less(BinOp): pass

@replaces(ast.More)
class More(BinOp): pass

@replaces(ast.Sub)
class Sub(BinOp): pass

@replaces(ast.Pow)
class Pow(BinOp): pass

@replaces(ast.Subscript)
class Subscript(BinOp):
  same_type_operands = False


@replaces(ast.Parens)
class Parens(Unary):
  def eval(self, frame):
    return self.arg.eval(frame)


@replaces(ast.IfThen)
class IfThen(ast.IfThen):
  def eval(self, frame):
    if self.iff.eval(frame):  # this should return Bool
      return True, self.then.eval(frame)
    return False, 0


@replaces(ast.Match)
class Match(Unary):
  def eval(self, frame):
    for expr in self.arg:
      assert isinstance(expr, IfThen), \
        "Child nodes of match operator can" \
        "only be instances of IfThen"
      match, result = expr.eval(frame)
      if match:
        return result


@replaces(ast.AlwaysTrue)
class AlwaysTrue(Value):
  def Bool(self, frame):
    return Bool(True)


@replaces(ast.Call0)
class Call0(Unary):
  def eval(self, frame):
    func = self.arg.eval(frame)
    return func.Call(frame)


@replaces(ast.Comment)
class Comment(Value):
  def eval(self, frame):
    pass


def run(ast, args=['<progname>']):
  ast = rewrite(ast, replace_nodes)
  log.final_ast("the final AST is:\n", ast)

  frame = Frame()
  ast.eval(frame)
  log.topframe("the top frame is\n", frame)

  if 'main' not in frame:
    print("no main function defined, exiting")
    return

  with frame as newframe:
    newframe['argc'] = Int(len(args))
    newframe['argv'] = Array(*map(Str, args))
    newframe['main'].Call(newframe)