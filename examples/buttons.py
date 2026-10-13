"""Buttons in LFS: one to click, one to type into. Type !buttons in LFS to show them, !hide to
remove them.

LFS must be listening for InSim: type /insim=29999 in LFS first.
"""

from lfs_insim import Command, Commands, InSim, received
from lfs_insim.packets import BFN, IS_BFN, IS_BTN, ISB


def buttons(insim: InSim) -> None:
    """A plugin with buttons of its own."""
    commands = insim.use(Commands)
    # Each button needs a ClickID (0 to 239) that no other plugin uses: ask the InSim for them.
    click_me, type_here = insim.reserve_click_ids(2)
    clicks = 0

    def show(ucid: int) -> None:
        """Send both buttons to a connection. Sending one again with its ClickID updates it."""
        insim.send(
            IS_BTN(
                ReqI=1,  # LFS needs it non-zero
                UCID=ucid,  # 0 = this computer, 255 = everyone
                ClickID=click_me,
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
                ClickID=type_here,
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
    def show_them(command: Command) -> None:
        show(command.ucid)

    @commands.on_command("hide")
    def hide(command: Command) -> None:
        # Only this plugin's buttons: BFN.CLEAR would remove every plugin's
        insim.send(
            IS_BFN(SubT=BFN.DEL_BTN, UCID=command.ucid, ClickID=click_me, ClickMax=type_here)
        )

    @insim.on.IS_BTC
    def clicked(packet: received.IS_BTC) -> None:
        nonlocal clicks
        if packet.ClickID == click_me:
            clicks += 1
            show(packet.UCID)

    @insim.on.IS_BTT
    def typed(packet: received.IS_BTT) -> None:
        if packet.ClickID == type_here:
            insim.say(f"You typed: {packet.Text}", to=packet.UCID)


if __name__ == "__main__":
    insim = InSim(name="buttons", prefix="!")
    insim.use(buttons)
    insim.run()
