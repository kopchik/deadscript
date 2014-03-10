#!/usr/bin/env python3

from log import logfilter
from ast import parse, pretty_print
from tokenizer import tokenize
from indent import parse as indent_parse
from interpreter import run
import argparse
from sys import exit

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-t', '--tokens', action='store_const', const=True,
                      default=False, help="show tokens")
  parser.add_argument('-a', '--ast', action='store_const', const=True,
                      default=False, help="show abstract syntax tree")
  parser.add_argument('-d', '--debug', action='store_const', const=True,
                      default=False, help="show intermediate output")
  parser.add_argument('-n', '--dry-run', action='store_const', const=True,
                      default=False, help="do not execute the program")
  parser.add_argument('input', help="path to file")
  parser.add_argument('cmd', nargs="*")
  args = parser.parse_args()

  logfilter.rules = [
    # ('interpreter.*', False),
    # ('indent.*', False)
  ]

  if args.debug: logfilter.default = True
  else:          logfilter.default = False

  with open(args.input) as fd:
    # split source into tokens
    src = fd.read()
    tokens = tokenize(src)
    if args.tokens:
      print(tokens)

    # parse indentation
    ast = indent_parse(tokens)

    # finalize AST generation
    ast = parse(ast)
    if args.ast:
      pretty_print(ast)

    cmd = [args.input]+args.cmd
    # run the program
    if not args.dry_run:
      exit(run(ast, cmd))