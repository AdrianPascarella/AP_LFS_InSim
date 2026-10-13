# lfs_insim documentation

1. [Getting started](getting-started.md): install, let LFS listen, write and run a first program.
2. [InSim](insim.md): handlers, chat commands, sending, asking LFS, running on a rhythm, buttons.
3. [Who is who, and text](roster-and-text.md): `Roster`, and how LFS text (colours, escapes) arrives.
4. [OutSim and OutGauge](outsim-outgauge.md): the UDP data, alone or together with InSim.

Runnable programs are in [`examples/`](../examples). Every packet class and field is named as in
the official [InSim.txt](https://www.lfs.net/programmer/insim) specification (`IS_NPL.PName`,
`IS_STA.NumP`...); the editor shows them, and their docstrings come from the specification.
