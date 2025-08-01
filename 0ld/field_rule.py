from typing import Optional
from dataclasses import dataclass

@dataclass
class FieldRule:
    """Règle de validation pour un champ spécifique"""
    name: str
    pattern: str
    description: str
    validator_func: Optional[callable] = None
    expected_position: Optional[int] = None  # Position attendue dans l'ordre séquentiel