main = (argc, argv) ->
  p "number of args: {argc}"
  otherwise = _
  match
    argc == 1 => p "Hello, anonymus!"
    argc == 2 =>
        name = argv[1]
        p "Hello, {name}!"
    otherwise => p "Too many parameters! CMD: {argv}"
