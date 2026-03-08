from dataclasses import dataclass, field


@dataclass
class DictionaryEntry:
    word: str
    description: str
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "word": self.word,
            "description": self.description,
            "examples": self.examples,
        }
