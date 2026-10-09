# Specification 07: Scientific Text Normalization & TTS Lexicon

## 1. Objective
Ensure the AI sounds like a natural, fluent astronomy educator by converting scientific notation, abbreviations, mathematical formulas, and astronomical catalogs into spoken English *before* passing the text to Kokoro TTS.

## 2. Architecture & Pipeline Location
This module acts as a middleware filter.
**Flow:** `AstroSage-8B (Raw Tokens)` → `Sentence Boundary Buffer` → `Text Normalizer` → `Kokoro TTS` → `WebSocket`

## 3. Core Normalization Rules
The Python normalization layer must use Regular Expressions (RegEx) and dictionary lookups to handle the following categories:

### A. Astronomical Objects & Catalogs
- `Sagittarius A*` → "Sagittarius A star"
- `Sgr A*` → "Sagittarius A star"
- `JWST` → "James Webb Space Telescope" (Never "J-W-S-T")
- `M87` / `M 87` → "Messier 87"
- `NGC \d+` → Read as individual numbers (e.g., `NGC 1976` → "N G C nineteen seventy-six")

### B. Mathematical & Scientific Notation
- `~` before a number → "approximately"
- `× 10^` / `x 10^` / `e+` → "times ten to the power of"
- Mass notation: `M☉` or `solar masses` → "solar masses"
- Distance: `ly` → "light-years", `pc` → "parsecs", `AU` → "astronomical units"
- Temperature: `K` (when following a number) → "Kelvin"
- Speeds: `km/s` → "kilometers per second", `c` (in context of speed) → "the speed of light"

### C. Number Formatting
- Expand massive numbers into spoken words to prevent TTS stuttering.
- `4.6 billion` → Ensure TTS does not pause at the decimal.
- Years: `2026` → "twenty twenty-six" (not "two thousand and twenty-six" unless appropriate).

## 4. Implementation Steps
1. **Module Creation:** Create a `tts_normalizer/` module in the Python backend.
2. **Rule Engine:** Build a class containing compiled RegEx patterns and a static replacement dictionary for the rules listed in Section 3.
3. **Pipeline Injection:** Import the normalizer into the WebSocket streaming loop. When the sentence buffer detects a complete sentence from the LLM, pass it through `Normalizer.clean(text)` before submitting it to Kokoro-ONNX.
4. **Unit Testing:** Write a strict `pytest` suite feeding raw scientific sentences into the normalizer and asserting the output matches the phonetic expectations.