"""Helpers geométricos sobre listas de nodos (sin estado propio).

Candidatos a mudarse a `nav_modes/freeroam/geometry.py` si algún día los
necesita alguien más: no dependen de nada de `_TrafficMixin`."""

from __future__ import annotations

import math
from typing import List

from insims.ai_control.base import _MixinBase
from insims.users_management.main import Coordinates


class _PathsMixin(_MixinBase):
    def _get_lookahead_point(
        self,
        my_x: float,
        my_y: float,
        node_index: int,
        nodes_list: list,
        lookahead_m: float,
        reverse: bool = False,
    ) -> tuple[float, float]:
        if not nodes_list:
            return my_x, my_y

        indices = (
            range(node_index, -1, -1) if reverse else range(node_index, len(nodes_list))
        )

        prev_x, prev_y = my_x, my_y
        accumulated = 0.0
        for idx in indices:
            node = nodes_list[idx]
            seg_len = math.hypot(node.x_m - prev_x, node.y_m - prev_y)
            if accumulated + seg_len >= lookahead_m:
                t = (lookahead_m - accumulated) / seg_len if seg_len > 0 else 0.0
                return prev_x + t * (node.x_m - prev_x), prev_y + t * (
                    node.y_m - prev_y
                )
            accumulated += seg_len
            prev_x, prev_y = node.x_m, node.y_m

        last = nodes_list[0 if reverse else -1]
        return last.x_m, last.y_m

    def _calc_path_length(self, nodes: List[Coordinates], start_idx: int = 0) -> float:
        """
        Calcula la distancia real de un trazado sumando la distancia entre sus nodos
        a partir de un índice específico.
        """
        if not nodes or start_idx >= len(nodes) - 1:
            return 0.0

        total_dist = 0.0
        # Nos aseguramos de que el índice inicial no sea negativo
        start_idx = max(0, start_idx)

        for i in range(start_idx, len(nodes) - 1):
            p1 = nodes[i]
            p2 = nodes[i + 1]
            # Usamos math.hypot (2D) por rendimiento, ya que para longitudes de asfalto
            # suele ser más que suficiente salvo que haya pendientes extremas.
            total_dist += math.hypot(p2.x_m - p1.x_m, p2.y_m - p1.y_m)

        return total_dist
