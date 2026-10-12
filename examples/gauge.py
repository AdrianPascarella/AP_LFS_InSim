"""A fixed rhythm, async and OutGauge at once: every 2 s, show the speed of your car in LFS.

LFS must be listening for InSim (type /insim=29999 in LFS) and sending OutGauge: with LFS
closed, set these lines in its cfg.txt: "OutGauge Mode 1" and "OutGauge Port 30001".
"""

from lfs_insim import InSim, OutGauge, run
from lfs_insim.packets import IS_MSL, IS_STA, OutGaugePack

insim = InSim(name="gauge")
gauge = OutGauge(port=30001)  # UDP; port 30000 is often taken by other programs

latest: OutGaugePack | None = None


@gauge.on(OutGaugePack)
def dashboard(packet: OutGaugePack) -> None:
    global latest
    latest = packet  # up to 100 a second: keep the last one, and act on a rhythm


@insim.every(2)
async def show() -> None:
    state = await insim.request(IS_STA)  # waits for LFS without stopping anything else
    if latest is None:
        text = "No OutGauge data yet: is a car on track?"
    else:
        text = f"{latest.Speed * 3.6:.0f} km/h at {latest.RPM:.0f} rpm"
    insim.send(IS_MSL(Msg=f"{text} ({state.NumP} in the race)"))  # only on this computer


if __name__ == "__main__":
    run(insim, gauge)  # one program, both sources
