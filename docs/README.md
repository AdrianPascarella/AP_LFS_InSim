# lfs_insim documentation

1. [Getting started](getting-started.md): install, let LFS listen, write and run a first program.
2. [InSim](insim.md): handlers, chat commands, sending, asking LFS, running on a rhythm, buttons.
3. [Plugins](plugins.md): a program in parts, alone or combined; sharing the Roster and the commands.
4. [Who is who, and text](roster-and-text.md): `Roster`, your own state with `watch()`, and how LFS text (colours, escapes) arrives.
5. [OutSim and OutGauge](outsim-outgauge.md): the UDP data, alone or together with InSim.
6. [Units](units.md): positions, speeds and angles in metres, km/h and degrees.
7. [Testing without LFS](testing.md): `lfs_insim.testing.FakeLFS`, to test a program or a plugin without the game.
8. [Packets by direction](packets.md): which packets LFS sends, which your program sends, and which go both ways.

Runnable programs are in [`examples/`](../examples). Every packet class and field is named as in
the official [InSim.txt](https://www.lfs.net/programmer/insim) specification (`IS_NPL.PName`,
`IS_STA.NumP`...); the editor shows them, and their docstrings come from the specification.
