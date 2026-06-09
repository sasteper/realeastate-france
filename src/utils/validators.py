"""
Input validation utilities for the IAD property estimator GUI.

Author: [Twoje Imię i Nazwisko]
License: MIT
"""

from typing import Optional


def validate_surface(value: str) -> tuple[bool, Optional[float], str]:
    """
    Validate property surface area input.

    Args:
        value: Raw string from the input field.

    Returns:
        Tuple of (is_valid, parsed_float_or_None, error_message).
    """
    value = value.strip().replace(",", ".")
    if not value:
        return False, None, "Pole wymagane"
    try:
        v = float(value)
    except ValueError:
        return False, None, "Podaj liczbę (np. 85)"
    if v <= 0:
        return False, None, "Powierzchnia musi być > 0"
    if v > 5000:
        return False, None, "Max 5 000 m²"
    return True, v, ""


def validate_bedrooms(value: str) -> tuple[bool, Optional[int], str]:
    """
    Validate number of bedrooms input.

    Args:
        value: Raw string from the input field.

    Returns:
        Tuple of (is_valid, parsed_int_or_None, error_message).
    """
    value = value.strip()
    if not value:
        return False, None, "Pole wymagane"
    try:
        v = int(float(value))
    except ValueError:
        return False, None, "Podaj liczbę całkowitą"
    if v < 0:
        return False, None, "Min 0"
    if v > 20:
        return False, None, "Max 20"
    return True, v, ""


def validate_image_count(value: str) -> tuple[bool, Optional[int], str]:
    """
    Validate number of listing images.

    Args:
        value: Raw string from the input field.

    Returns:
        Tuple of (is_valid, parsed_int_or_None, error_message).
    """
    value = value.strip()
    if not value:
        return False, None, "Pole wymagane"
    try:
        v = int(float(value))
    except ValueError:
        return False, None, "Podaj liczbę całkowitą"
    if v < 1:
        return False, None, "Min 1"
    if v > 30:
        return False, None, "Max 30"
    return True, v, ""
