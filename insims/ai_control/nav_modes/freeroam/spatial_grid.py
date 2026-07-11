"""Índice espacial (hash grid uniforme 2D) para acelerar la localización
geométrica en mapas freeroam grandes.

El problema: la búsqueda del road más cercano recorría TODOS los nodos del mapa
(O(nodos totales); ~11k nodos en south_city ampliado → ~ms por consulta). Este
grid reduce esa búsqueda a O(vecindario): cada segmento se registra en todas las
celdas de su *bounding-box*, y una consulta solo mira las celdas alrededor del
punto, expandiéndose en anillos hasta poder GARANTIZAR que nada fuera de lo ya
visto puede estar más cerca.

Es deliberadamente genérico —guarda ids en celdas y responde qué ids caen en un
anillo o bloque— para poder reutilizarse en el radar de vehículos (Fase b). Quien
lo usa aporta la métrica de distancia real; el grid solo acota con la geometría
de las celdas (garantía de anillos), nunca calcula distancias.

**Garantía de corrección (base de la parada temprana):** para un punto `p` en la
celda central, cualquier celda a distancia Chebyshev `m` tiene su punto más
cercano a `p` a >= (m-1)*cell del propio `p`. Registrando cada segmento en TODAS
las celdas de su bounding-box, la celda que contiene el punto del segmento más
cercano a `p` siempre está registrada. Por tanto, tras mirar los anillos 0..k, un
segmento visto solo en anillos > k dista >= k*cell de `p`: si el mejor encontrado
dista < k*cell, es el mínimo global.
"""

from __future__ import annotations

import math
from typing import Dict, Hashable, Iterator, List, Optional, Tuple

Cell = Tuple[int, int]


class SpatialHashGrid:
    """Hash grid uniforme 2D en metros. Mapea celda -> lista de ids."""

    def __init__(self, cell_size_m: float):
        if cell_size_m <= 0:
            raise ValueError("cell_size_m debe ser > 0")
        self.cell_size_m: float = float(cell_size_m)
        self._cells: Dict[Cell, List[Hashable]] = {}
        # Bounds de las celdas OCUPADAS (para saber cuándo un bloque ya las cubre
        # todas y seguir expandiendo no puede añadir candidatos nuevos).
        self._min_ix: Optional[int] = None
        self._max_ix: Optional[int] = None
        self._min_iy: Optional[int] = None
        self._max_iy: Optional[int] = None

    # ------------------------------------------------------------------ #
    # Construcción
    # ------------------------------------------------------------------ #
    def _cell_of(self, x: float, y: float) -> Cell:
        c = self.cell_size_m
        return (math.floor(x / c), math.floor(y / c))

    def _add(self, ix: int, iy: int, item_id: Hashable) -> None:
        bucket = self._cells.get((ix, iy))
        if bucket is None:
            self._cells[(ix, iy)] = [item_id]
        else:
            bucket.append(item_id)

        if self._min_ix is None:
            self._min_ix = self._max_ix = ix
            self._min_iy = self._max_iy = iy
        else:
            if ix < self._min_ix:
                self._min_ix = ix
            if ix > self._max_ix:
                self._max_ix = ix
            if iy < self._min_iy:
                self._min_iy = iy
            if iy > self._max_iy:
                self._max_iy = iy

    def insert_point(self, item_id: Hashable, x: float, y: float) -> None:
        """Registra un id en la celda de un punto."""
        ix, iy = self._cell_of(x, y)
        self._add(ix, iy, item_id)

    def insert_segment(
        self, item_id: Hashable, ax: float, ay: float, bx: float, by: float
    ) -> None:
        """Registra un id en TODAS las celdas del bounding-box del segmento A-B.

        El bounding-box es un superconjunto de las celdas que el segmento cruza
        realmente (basta para la garantía de corrección; los segmentos de road
        son cortos frente a la celda, así que sobran 0-1 celdas de más)."""
        ix0, iy0 = self._cell_of(min(ax, bx), min(ay, by))
        ix1, iy1 = self._cell_of(max(ax, bx), max(ay, by))
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                self._add(ix, iy, item_id)

    # ------------------------------------------------------------------ #
    # Consulta
    # ------------------------------------------------------------------ #
    @property
    def is_empty(self) -> bool:
        return not self._cells

    def ring_ids(self, px: float, py: float, k: int) -> Iterator[Hashable]:
        """Itera los ids registrados en el anillo Chebyshev de radio `k`
        alrededor del punto (k=0 -> la celda central; k>0 -> solo el marco
        exterior del bloque (2k+1)²). Puede repetir ids: dedúplquelos el llamador.
        """
        cx, cy = self._cell_of(px, py)
        cells = self._cells
        if k == 0:
            bucket = cells.get((cx, cy))
            if bucket:
                yield from bucket
            return
        # Filas superior e inferior (incluyen esquinas).
        for ix in range(cx - k, cx + k + 1):
            for iy in (cy - k, cy + k):
                bucket = cells.get((ix, iy))
                if bucket:
                    yield from bucket
        # Columnas izquierda y derecha (sin esquinas, ya cubiertas).
        for iy in range(cy - k + 1, cy + k):
            for ix in (cx - k, cx + k):
                bucket = cells.get((ix, iy))
                if bucket:
                    yield from bucket

    def ids_within(self, px: float, py: float, radius: float) -> Iterator[Hashable]:
        """Itera los ids de las celdas que solapan la caja
        [px-radius, px+radius] x [py-radius, py+radius] alrededor del punto.

        Es un SUPERCONJUNTO de los ids cuyo punto dista <= `radius` del centro
        (la caja contiene el círculo) → nunca produce falsos negativos. Puede
        repetir ids (un segmento ocupa varias celdas): dedúplquelos el llamador,
        que además aplica la distancia real. `radius < 0` no devuelve nada.

        Complementa a `ring_ids` (vecino más cercano): esta es la consulta de
        REGIÓN que usa el radar de vehículos (grid dinámico), donde interesan
        TODOS los vehículos dentro de un radio, no solo el más cercano.
        """
        if radius < 0:
            return
        ix0, iy0 = self._cell_of(px - radius, py - radius)
        ix1, iy1 = self._cell_of(px + radius, py + radius)
        cells = self._cells
        for ix in range(ix0, ix1 + 1):
            for iy in range(iy0, iy1 + 1):
                bucket = cells.get((ix, iy))
                if bucket:
                    yield from bucket

    def block_covers_all(self, px: float, py: float, k: int) -> bool:
        """True si el bloque (2k+1)² centrado en el punto ya contiene todas las
        celdas ocupadas → expandir más no añade candidatos (parada segura)."""
        if self.is_empty:
            return True
        cx, cy = self._cell_of(px, py)
        return (
            cx - k <= self._min_ix
            and cx + k >= self._max_ix
            and cy - k <= self._min_iy
            and cy + k >= self._max_iy
        )


__all__ = ["SpatialHashGrid"]
