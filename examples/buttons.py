"""Buttons in LFS: one to click, one to type into. Type !buttons in LFS to show them, !hide to
remove them.

LFS must be listening for InSim: type /insim=29999 in LFS first.
"""

from lfs_insim import Command, Commands, InSim, received
from lfs_insim.packets import BFN, IS_BTN, ISB

insim = InSim(name="buttons", prefix="!")
commands = insim.use(Commands)

CLICK_ME, TYPE_HERE = 1, 2  # ClickID: each button of this program needs its own (0 to 239)
clicks = 0


def show(ucid: int) -> None:
    """Send both buttons to a connection. Sending one again with its ClickID updates it."""
    insim.send(
        IS_BTN(
            ReqI=1,  # LFS needs it non-zero
            UCID=ucid,  # 0 = this computer, 255 = everyone
            ClickID=CLICK_ME,
            BStyle=ISB.CLICK | ISB.LIGHT,
            L=70,  # position and size: the screen is 200 x 200
            T=40,
            W=60,
            H=8,
            Text=f"Clicked {clicks} times",
        ),
        IS_BTN(
            ReqI=1,
            UCID=ucid,
            ClickID=TYPE_HERE,
            BStyle=ISB.CLICK | ISB.DARK,
            TypeIn=20,  # clicking opens a text box for up to 20 characters
            L=70,
            T=50,
            W=60,
            H=8,
            Text="Type something",
            Caption="Your text",
        ),
    )


@commands.on_command("buttons")
def buttons(command: Command) -> None:
    show(command.ucid)


@commands.on_command("hide")
def hide(command: Command) -> None:
    insim.send.IS_BFN(SubT=BFN.CLEAR, UCID=command.ucid)


@insim.on.IS_BTC
def clicked(packet: received.IS_BTC) -> None:
    global clicks
    if packet.ClickID == CLICK_ME:
        clicks += 1
        show(packet.UCID)


@insim.on.IS_BTT
def typed(packet: received.IS_BTT) -> None:
    if packet.ClickID == TYPE_HERE:
        insim.say(f"You typed: {packet.Text}", to=packet.UCID)


if __name__ == "__main__":
    insim.run()
