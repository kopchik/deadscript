main = (argc, argv) ->
  switch argc
    0 => p "Hello, anonymus!"
    2 =>
        name = argv[1]
        p "Hello, {name}!"
    _ => p "Hello, {argv}"
