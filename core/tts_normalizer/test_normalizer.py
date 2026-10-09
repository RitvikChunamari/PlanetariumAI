import pytest
from tts_normalizer.normalizer import TextNormalizer

@pytest.fixture
def normalizer():
    return TextNormalizer()

def test_astronomical_objects(normalizer):
    assert normalizer.clean("Sagittarius A* is a black hole.") == "Sagittarius A star is a black hole."
    assert normalizer.clean("Sgr A* is cool.") == "Sagittarius A star is cool."
    assert normalizer.clean("The JWST launched recently.") == "The James Webb Space Telescope launched recently."
    assert normalizer.clean("Look at M87 and M 87.") == "Look at Messier 87 and Messier 87."
    assert normalizer.clean("NGC 1976 is the Orion Nebula.") == "N G C 1976 is the Orion Nebula."

def test_math_and_scientific(normalizer):
    assert normalizer.clean("The mass is ~5 kg.") == "The mass is approximately 5 kg."
    assert normalizer.clean("Speed is 3.0 x 10^8 m/s.") == "Speed is 3.0 times ten to the power of 8 meters per second."
    assert normalizer.clean("Speed is 3.0 × 10^8 m/s.") == "Speed is 3.0 times ten to the power of 8 meters per second."
    assert normalizer.clean("Value is 5e+9 or 4e-3.") == "Value is 5 times ten to the power of 9 or 4 times ten to the power of -3."
    
    assert normalizer.clean("Mass is 5 M☉.") == "Mass is 5 solar masses."
    assert normalizer.clean("Mass is 5 solar masses.") == "Mass is 5 solar masses." # unaffected
    assert normalizer.clean("It is 10 ly away.") == "It is 10 light-years away."
    assert normalizer.clean("It is 4.2 pc away.") == "It is 4.2 parsecs away."
    assert normalizer.clean("It is 1.5 AU away.") == "It is 1.5 astronomical units away."

def test_temperature_and_speed(normalizer):
    assert normalizer.clean("It is 5000 K on the surface.") == "It is 5000 Kelvin on the surface."
    assert normalizer.clean("Velocity is 200 km/s.") == "Velocity is 200 kilometers per second."
    assert normalizer.clean("It moves at 0.1c relative to us.") == "It moves at 0.1 times the speed of light relative to us."

def test_number_formatting(normalizer):
    assert normalizer.clean("It is 4.6 billion years old.") == "It is 4 point 6 billion years old."
    assert normalizer.clean("In the year 2026, we will go.") == "In the year twenty 26, we will go."
    assert normalizer.clean("2015 was a good year.") == "twenty 15 was a good year."
