main = (argc, argv) ->
  match
    argc == 0 => p "Hello, anonymus!"
    argc == 2 =>
        name = argv[1]
        p "Hello, {name}!"
    _ => p "Hello, {argv}"
