succ = (arg) -> arg + 1

main = (argc, argv) ->
  assert 1 + 1 == 2
  assert 1 < 2
  assert 2 > 1
  assert 1 + 2 * 3 == 7
  assert (1 + 2)*3 == 9
  assert 2^1^2 == 2
  assert (2^1)^2 == 4
  assert succ succ 1 == 3
  #assert succ . succ 1 == 3
  #assert succ 0 $ succ $ succ = 3
  match
    argc == 1  => p "I've got just 1 argument: {argv}"
    _          => p "I've got {argc} arguments: {argv}"
