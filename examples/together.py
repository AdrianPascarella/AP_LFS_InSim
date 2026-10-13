"""Several plugins in one program: hello, who and buttons share one connection to LFS, one
Roster and one set of chat commands. Type !hello, !who or !buttons in LFS.

LFS must be listening for InSim: type /insim=29999 in LFS first. Run it from this folder, next to
hello.py, who.py and buttons.py.
"""

from buttons import buttons
from hello import hello
from who import who

from lfs_insim import InSim

insim = InSim(name="together", prefix="!")
insim.use(hello)
insim.use(who)
insim.use(buttons)

if __name__ == "__main__":
    insim.run()
