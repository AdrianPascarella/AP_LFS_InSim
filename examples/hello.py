"""Answer a chat command: type !hello in LFS and it answers you.

LFS must be listening for InSim: type /insim=29999 in LFS first.
"""

from lfs_insim import Command, Commands, InSim, received


def hello(insim: InSim) -> None:
    """A plugin: `insim.use(hello)` adds it to any InSim, alone or with other plugins."""
    commands = insim.use(Commands)

    @insim.on.IS_VER
    def connected(packet: received.IS_VER) -> None:
        print(f"Connected to LFS {packet.Version}, InSim {packet.InSimVer}")

    @commands.on_command("hello")
    def answer(command: Command) -> None:
        command.reply("Hello from Python")


if __name__ == "__main__":
    insim = InSim(name="hello", prefix="!")  # admin_password="..." if LFS has one
    insim.use(hello)
    insim.run()  # blocks until Ctrl+C; reconnects on its own if LFS restarts
