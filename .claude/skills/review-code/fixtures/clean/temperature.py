"""Convert between Celsius and Fahrenheit."""


def c_to_f(celsius: float) -> float:
    """Return the Fahrenheit equivalent of a Celsius temperature."""
    return celsius * 9 / 5 + 32


def f_to_c(fahrenheit: float) -> float:
    """Return the Celsius equivalent of a Fahrenheit temperature."""
    return (fahrenheit - 32) * 5 / 9
