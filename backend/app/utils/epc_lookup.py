"""
EPC Translation Utility

Loads and caches product metadata from epc_translation.csv.
At scale, this would be replaced by API calls to Decathlon's product database.
For the demo environment with 26 RFID tags, a local CSV is sufficient.
"""
import csv
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ProductMetadata:
    """Product information from EPC translation table"""
    epc: str
    name: str
    category: str
    size: str
    color: str
    price_chf: float
    gtin: str
    serial_number: str


class EPCLookup:
    """Singleton cache for EPC to product metadata lookups"""
    
    _instance = None
    _cache: Dict[str, ProductMetadata] = {}
    _loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, csv_path: Optional[Path] = None) -> None:
        """Load EPC translations from CSV file"""
        if self._loaded:
            return
            
        if csv_path is None:
            # Default path relative to backend directory
            csv_path = Path(__file__).parent.parent.parent / "epc_translation.csv"
        
        if not csv_path.exists():
            print(f"Warning: EPC translation file not found at {csv_path}")
            self._loaded = True
            return
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    epc = row['epc'].strip().lower()  # Normalize to lowercase
                    metadata = ProductMetadata(
                        epc=epc,
                        name=row['name'].strip(),
                        category=row['category'].strip(),
                        size=row['size'].strip(),
                        color=row['color'].strip(),
                        price_chf=float(row['price_chf']),
                        gtin=row['gtin'].strip(),
                        serial_number=row['serialNumber'].strip()
                    )
                    self._cache[epc] = metadata
            
            print(f"Loaded {len(self._cache)} EPC translations from {csv_path}")
            self._loaded = True
            
        except Exception as e:
            print(f"Error loading EPC translations: {e}")
            self._loaded = True
    
    def lookup(self, epc: str) -> Optional[ProductMetadata]:
        """Look up product metadata by EPC code (case-insensitive)"""
        if not self._loaded:
            self.load()
        
        epc_normalized = epc.strip().lower()
        return self._cache.get(epc_normalized)
    
    def get_product_name(self, epc: str, include_details: bool = True) -> str:
        """
        Get formatted product name for display
        
        Args:
            epc: EPC code to look up
            include_details: If True, includes size/color (e.g., "Hiking Jacket - Size M - Black")
                           If False, returns just the base name
        
        Returns:
            Formatted product name or generic fallback
        """
        metadata = self.lookup(epc)
        if metadata is None:
            return f"Demo Item {epc[:8]}"
        
        if include_details:
            if metadata.size and metadata.size.lower() != 'onesize':
                return f"{metadata.name} - Size {metadata.size} - {metadata.color}"
            else:
                return f"{metadata.name} - {metadata.color}"
        
        return metadata.name


# Global singleton instance
epc_lookup = EPCLookup()
