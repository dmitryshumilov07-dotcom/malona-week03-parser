from parser.adapters.base import BaseAdapter, LookupResult
from parser.adapters.blum import BlumAdapter
from parser.adapters.boyard import BoyardAdapter
from parser.adapters.dinastiya import DinastiyaAdapter
from parser.adapters.kvadrat import KvadratAdapter
from parser.adapters.makmart import MakmartAdapter
from parser.adapters.mdm_complect import MdmComplectAdapter
from parser.adapters.nt74 import Nt74Adapter

ADAPTERS: dict[str, type[BaseAdapter]] = {
    "blum": BlumAdapter,
    "mdm_complect": MdmComplectAdapter,
    "kvadrat": KvadratAdapter,
    "boyard": BoyardAdapter,
    "dinastiya": DinastiyaAdapter,
    "makmart": MakmartAdapter,
    "nt74": Nt74Adapter,
}

__all__ = [
    "ADAPTERS",
    "BaseAdapter",
    "LookupResult",
    "BlumAdapter",
    "MdmComplectAdapter",
    "KvadratAdapter",
    "BoyardAdapter",
    "DinastiyaAdapter",
    "MakmartAdapter",
    "Nt74Adapter",
]
