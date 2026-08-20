import time

from gpiozero import OutputDevice


# AI assistance: ChatGPT helped me adapt the previously tested SmartBlock
# relay logic for Raspberry Pi GPIO control.

RELAY_GPIO_PIN = 17
PULSE_DURATION_SECONDS = 1.5


def open_barrier():
    """Send one pulse to the barrier relay."""

    barrier_relay = OutputDevice(
        RELAY_GPIO_PIN,
        active_high=False,
        initial_value=False
    )

    try:
        barrier_relay.on()
        time.sleep(PULSE_DURATION_SECONDS)

    finally:
        barrier_relay.off()
        time.sleep(1)
        barrier_relay.close()