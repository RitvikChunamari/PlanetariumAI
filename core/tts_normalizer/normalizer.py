import re

class TextNormalizer:
    def __init__(self):
        # A list of tuples (pattern, replacement) evaluated in order
        self.rules = [
            # A. Astronomical Objects & Catalogs
            (r"\bSagittarius A\*", "Sagittarius A star"),
            (r"\bSgr A\*", "Sagittarius A star"),
            (r"\bJWST\b", "James Webb Space Telescope"),
            (r"\bM\s*(\d+)\b", r"Messier \1"),
            # NGC \d+ is handled fairly well by TTS naturally if spaced as N G C
            # But let's enforce N G C spelling to prevent it reading as a single word
            (r"\bNGC\s+(\d+)\b", r"N G C \1"),
            
            # B. Mathematical & Scientific Notation
            # ~ before a number
            (r"~\s*(?=\d)", "approximately "),
            # Scientific notation
            (r"\s*[x×]\s*10\^(-?\d+)", r" times ten to the power of \1"),
            (r"(?<=\d)e\+?(-?\d+)\b", r" times ten to the power of \1"),
            # Mass notation
            (r"\bM☉", "solar masses"),
            # Distance
            (r"\b(\d+(?:\.\d+)?)\s*ly\b", r"\1 light-years"),
            (r"\b(\d+(?:\.\d+)?)\s*pc\b", r"\1 parsecs"),
            (r"\b(\d+(?:\.\d+)?)\s*AU\b", r"\1 astronomical units"),
            # Temperature
            (r"\b(\d+(?:\.\d+)?)\s*K\b", r"\1 Kelvin"),
            (r"\b(\d+(?:\.\d+)?)\s*[°\ufffd]C\b", r"\1 degrees Celsius"),
            (r"\b(\d+(?:\.\d+)?)\s*C\b", r"\1 degrees Celsius"), # just in case it outputs 462C
            # Speeds
            (r"\bkm/s\b", "kilometers per second"),
            # speed of light c (e.g. 3.0 x 10^8 m/s, wait m/s is not specified but 3.0 x 10^8 m/s is in the goal!)
            (r"\bm/s\b", "meters per second"),
            
            # "fraction of c" or "0.1c" -> "0.1 times the speed of light"
            (r"\b(\d+(?:\.\d+)?)\s*c\b", r"\1 times the speed of light"),
        ]
        
        # Precompile regexes
        self.compiled_rules = [(re.compile(p), r) for p, r in self.rules]

    def clean(self, text: str) -> str:
        for pattern, replacement in self.compiled_rules:
            text = pattern.sub(replacement, text)
            
        # Specific fix for decimal followed by billions/millions to avoid pause, if needed
        text = re.sub(r"\b(\d+)\.(\d+)\s+(million|billion|trillion)\b", r"\1 point \2 \3", text)
        
        # Years: 2026 -> twenty twenty-six (or twenty 26, Kokoro will read 26 properly)
        text = re.sub(r"\b20([1-9]\d)\b", r"twenty \1", text)
        
        # Condense multiple spaces
        text = re.sub(r"\s+", " ", text).strip()
        
        return text
