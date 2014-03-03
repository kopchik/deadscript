from tokenizer import DENT
from log import Log
from copy import copy
from ast import Block, Expr
log = Log("indent")


def implicit_dents(tokens):
  tokens = copy(tokens)
  c = 0
  for i,t in enumerate(tokens):
    if isinstance(t, DENT):
      c = t.value
    elif hasattr(t, "sym") and t.sym == "->":
      for t in tokens[i:]:
        if isinstance(t, DENT):
          if t.value > c:
            tokens.insert(i+1, DENT(t.value))
          break
  return tokens


def merge_dents(tokens):
  tokens = copy(tokens)
  i = 0
  while i < len(tokens)-1:
    if isinstance(tokens[i], DENT) and isinstance(tokens[i+1], DENT):
      del tokens[i]
    else:
      i += 1
  return tokens


def blocks(it, lvl=0):
  expr = Expr()
  codeblk = Block(expr)
  prefix = "  "*lvl
  for t in it:
    # print(prefix, "got", t, end=' ')
    if isinstance(t, DENT):
      cur = t.value
      if cur == lvl and expr:
        # print(prefix, "new expr")
        expr = Expr()
        codeblk.append(expr)
        continue
      elif cur > lvl:
        # print(prefix, "nested block")
        r, cur = blocks(it, cur)
        # print(prefix, "got", r, cur, "from it")
        expr.append(r)
      if cur < lvl:
          # print(prefix, "time to return")
          return codeblk, cur
    else:
      # print(prefix, "adding it to current block")
      expr.append(t)
  return codeblk, lvl


def parse(tokens):
  tokens = implicit_dents(tokens)
  log.imp_dents("after adding implicit dents:\n", tokens)
  tokens = merge_dents(tokens)
  log.merge_dents("merging dents:\n", tokens)
  ast, _ = blocks(iter(tokens))
  log.blocks("after block parser:\n", ast)
  return ast