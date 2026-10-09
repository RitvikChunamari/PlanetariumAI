from rag.database import KnowledgeBase

facts = [
    "The Moon is moving away from Earth at a rate of about 3.8 centimeters per year.",
    "A year on Venus is shorter than a day on Venus.",
    "Olympus Mons on Mars is the tallest volcano in the solar system, about three times the height of Mount Everest.",
    "Jupiter has 95 officially recognized moons.",
    "The core of the Sun reaches temperatures of about 15 million degrees Celsius.",
    "Saturn's rings are mostly made of chunks of ice and rock.",
    "Uranus rotates on its side, making it unique among the planets in our solar system.",
    "Neptune has supersonic winds that can reach up to 2,100 kilometers per hour.",
    "Pluto is officially classified as a dwarf planet and resides in the Kuiper Belt.",
    "The Milky Way galaxy is estimated to contain between 100 billion and 400 billion stars.",
    "A neutron star is so dense that a single teaspoon of its material would weigh about 6 billion tons.",
    "The speed of light in a vacuum is exactly 299,792,458 meters per second.",
    "The Andromeda Galaxy is on a collision course with the Milky Way, expected to merge in about 4.5 billion years.",
    "Black holes are regions of space where gravity is so strong that nothing, not even light, can escape.",
    "The observable universe is estimated to be about 93 billion light-years in diameter.",
    "Voyager 1 is the farthest human-made object from Earth, having entered interstellar space in 2012.",
    "The James Webb Space Telescope is positioned at the second Lagrange point (L2), 1.5 million kilometers from Earth.",
    "Exoplanets are planets that orbit a star outside the solar system.",
    "A light-year is the distance light travels in one Earth year, about 9.46 trillion kilometers.",
    "The cosmic microwave background is the residual thermal radiation from the Big Bang."
]

if __name__ == "__main__":
    kb = KnowledgeBase()
    print("Seeding database...")
    kb.insert_facts(facts)
    print("Database seeded successfully.")
