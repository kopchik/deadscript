main = (argc, argv) ->
  p "number of args: {argc}"
  match
    argc == 1 => p "Hello, anonymus!"
    argc == 2 =>
        name = argv[1]
        p "Hello, {name}!"
    _ => p "Too many parameters! CMD: {argv}"
