import time

from gpiozero import Device, OutputDevice
from gpiozero.pins.mock import MockFactory


# AI assistance: ChatGPT helped me adapt the previously tested SmartBlock
# relay logic and implement mock GPIO for development on a Mac.

RELAY_GPIO_PIN = 17
PULSE_DURATION_SECONDS = 1.5


def open_barrier():
    """Send one pulse to the barrier relay."""

    # Use simulated GPIO when developing on a Mac
    Device.pin_factory = MockFactory()

    barrier_relay = OutputDevice(
        RELAY_GPIO_PIN,
        active_high=False,
        initial_value=False
    )

    try:
        print("Mock relay ON")
        barrier_relay.on()
        time.sleep(PULSE_DURATION_SECONDS)

    finally:
        barrier_relay.off()
        print("Mock relay OFF")
        time.sleep(1)
        barrier_relay.close()