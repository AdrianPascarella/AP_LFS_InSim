"""Tests unitarios del `SpatialHashGrid` (índice espacial de geometría, Fase 5).

Prueban el grid AISLADO (sin MapRecorder): inserción en celdas, iteración por
anillos Chebyshev y la cobertura de bloque que permite terminar la expansión. La
equivalencia con el barrido lineal de `get_location_context` se prueba aparte, en
`test_road_spatial_index.py`.
"""

from __future__ import annotations

import pytest

from insims.ai_control.nav_modes.freeroam.spatial_grid import SpatialHashGrid


class TestConstruccion:
    def test_cell_size_no_positivo_lanza(self):
        with pytest.raises(ValueError):
            SpatialHashGrid(0)
        with pytest.raises(ValueError):
            SpatialHashGrid(-5.0)

    def test_grid_vacio(self):
        g = SpatialHashGrid(10.0)
        assert g.is_empty
        assert list(g.ring_ids(0.0, 0.0, 0)) == []
        # Un grid vacío se considera "cubierto" a cualquier k (no hay nada que buscar).
        assert g.block_covers_all(0.0, 0.0, 0) is True


class TestInsertPoint:
    def test_punto_en_su_celda(self):
        g = SpatialHashGrid(10.0)
        g.insert_point("a", 5.0, 5.0)  # celda (0, 0)
        assert not g.is_empty
        assert list(g.ring_ids(5.0, 5.0, 0)) == ["a"]
        # Nada en el anillo 1 alrededor del mismo punto.
        assert list(g.ring_ids(5.0, 5.0, 1)) == []

    def test_celdas_negativas(self):
        g = SpatialHashGrid(10.0)
        g.insert_point("neg", -5.0, -5.0)  # floor(-0.5) = -1 → celda (-1, -1)
        assert list(g.ring_ids(-5.0, -5.0, 0)) == ["neg"]

    def test_punto_vecino_cae_en_anillo_1(self):
        g = SpatialHashGrid(10.0)
        g.insert_point("center", 5.0, 5.0)  # (0, 0)
        g.insert_point("right", 15.0, 5.0)  # (1, 0) → Chebyshev 1 desde (0,0)
        assert list(g.ring_ids(5.0, 5.0, 0)) == ["center"]
        assert list(g.ring_ids(5.0, 5.0, 1)) == ["right"]


class TestInsertSegment:
    def test_registra_todas_las_celdas_del_bbox(self):
        g = SpatialHashGrid(10.0)
        # Segmento horizontal de x=5 a x=25, y=5 → celdas (0,0),(1,0),(2,0).
        g.insert_segment("s", 5.0, 5.0, 25.0, 5.0)
        assert list(g.ring_ids(5.0, 5.0, 0)) == ["s"]  # celda (0,0)
        assert list(g.ring_ids(15.0, 5.0, 0)) == ["s"]  # celda (1,0)
        assert list(g.ring_ids(25.0, 5.0, 0)) == ["s"]  # celda (2,0)

    def test_segmento_diagonal_cubre_rectangulo(self):
        g = SpatialHashGrid(10.0)
        # De (5,5) a (25,25): bbox de celdas (0..2)x(0..2) = 9 celdas.
        g.insert_segment("d", 5.0, 5.0, 25.0, 25.0)
        # Una esquina del bbox que el segmento NO cruza igualmente lo contiene
        # (el bbox es superconjunto — suficiente para la garantía de corrección).
        assert list(g.ring_ids(25.0, 5.0, 0)) == ["d"]  # celda (2,0)

    def test_segmento_dentro_de_una_celda(self):
        g = SpatialHashGrid(10.0)
        g.insert_segment("tiny", 2.0, 2.0, 8.0, 8.0)  # todo en (0,0)
        assert list(g.ring_ids(2.0, 2.0, 0)) == ["tiny"]


class TestRingIds:
    def test_anillo_1_es_solo_el_marco(self):
        g = SpatialHashGrid(10.0)
        # 3x3 alrededor de (0,0): centro + 8 vecinos.
        coords = {
            "c": (5, 5),
            "n": (5, 15),
            "s": (5, -5),
            "e": (15, 5),
            "w": (-5, 5),
            "ne": (15, 15),
            "nw": (-5, 15),
            "se": (15, -5),
            "sw": (-5, -5),
        }
        for cid, (x, y) in coords.items():
            g.insert_point(cid, float(x), float(y))
        assert list(g.ring_ids(5.0, 5.0, 0)) == ["c"]
        ring1 = set(g.ring_ids(5.0, 5.0, 1))
        assert ring1 == {"n", "s", "e", "w", "ne", "nw", "se", "sw"}

    def test_id_repetido_en_varias_celdas_del_anillo(self):
        g = SpatialHashGrid(10.0)
        # Un id largo registrado en dos celdas distintas del MISMO anillo.
        g.insert_point("dup", 15.0, 5.0)  # (1,0)
        g.insert_point("dup", 15.0, 15.0)  # (1,1)
        ring1 = list(g.ring_ids(5.0, 5.0, 1))
        # ring_ids puede repetir; el llamador deduplica.
        assert ring1.count("dup") == 2


class TestBlockCoversAll:
    def test_cubre_cuando_el_bloque_abarca_las_celdas_ocupadas(self):
        g = SpatialHashGrid(10.0)
        g.insert_point("a", 5.0, 5.0)  # (0,0)
        g.insert_point("b", 15.0, 5.0)  # (1,0)
        # Desde (5,5): bounds ocupados ix 0..1, iy 0..0.
        assert g.block_covers_all(5.0, 5.0, 0) is False  # k=0 no llega a ix=1
        assert g.block_covers_all(5.0, 5.0, 1) is True  # 3x3 abarca todo

    def test_no_cubre_si_hay_celda_lejana(self):
        g = SpatialHashGrid(10.0)
        g.insert_point("near", 5.0, 5.0)  # (0,0)
        g.insert_point("far", 105.0, 5.0)  # (10,0)
        assert g.block_covers_all(5.0, 5.0, 1) is False
        assert g.block_covers_all(5.0, 5.0, 10) is True
