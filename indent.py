from tokenizer import DENT
from log import Log
log = Log("indent")


def implicit_dents(ast):
  c = 0
  for i,t in enumerate(ast):
    if isinstance(t, DENT):
      c = t.value
    elif hasattr(t, "sym") and t.sym == "->":
      for t in ast[i:]:
        if isinstance(t, DENT):
          if t.value > c:
            ast.insert(i+1, DENT(t.value))
          break
  return ast


def blocks(it, lvl=0):
  blk = []
  result = [blk]
  prefix = "  "*lvl
  for t in it:
    # print(prefix, "got", t, end=' ')
    if isinstance(t, DENT):
      cur = t.value
      if cur == lvl and blk:
        # print(prefix, "new statement")
        blk = []
        result.append(blk)
        continue
      elif cur > lvl:
        # print(prefix, "nested block")
        r, cur = blocks(it, cur)
        # print(prefix, "got", r, cur, "from it")
        blk.append(r)
      if cur < lvl:
          # print(prefix, "time to return")
          return result, cur
    else:
      # print(prefix, "adding it to current block")
      blk.append(t)
  return result, lvl


def parse(tokens):
  tokens = implicit_dents(tokens)
  log.imp_dents("after adding implicit dents:\n", tokens)

  ast, _ = blocks(iter(tokens))
  log.blocks("after block parser:\n", ast)
  return ast