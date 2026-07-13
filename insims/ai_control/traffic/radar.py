"""Radar de tráfico: barrido de vehículos en el carril propio, en el carril
objetivo de un adelantamiento y en el hueco de regreso.

Es el punto caliente del módulo: los 3 barridos consultan la rejilla espacial de
vehículos (`_build_vehicle_grid`, S28) en vez de recorrer los N → O(vecindario)
por consulta en vez de O(N) (O(N²) global)."""

from __future__ import annotations

import math
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING

from insims.ai_control.base import _MixinBase
from insims.ai_control.nav_modes.freeroam.graph import RoadLink
from insims.ai_control.nav_modes.freeroam.mode import FreeroamMode
from insims.ai_control.nav_modes.freeroam.spatial_grid import SpatialHashGrid
from lfs_insim.utils import calc_dist_3d

if TYPE_CHECKING:
    from insims.users_management.main import AI

# Tamaño de celda de la rejilla DINÁMICA de vehículos (m), independiente de la
# estática de geometría (S23). Las consultas del radar tienen radio ~max_dist+15
# (decenas de m); con una celda de este orden la caja de consulta abarca pocas
# celdas. El benchmark de W3 da una meseta plana de 40-80 m (por debajo penaliza
# el sondeo de celdas vacías; por encima, más candidatos por celda al agruparse
# las IAs); 50 m es el centro de la meseta. Ajustable.
_VEHICLE_GRID_CELL_M = 50.0

# Ventana de transición de un RoadLink (m), medida desde su nodo de ENTRADA. Dentro
# de ella el radar ensancha "mi carril" a la vía contigua de la cadena (ver
# `_lane_chain_ids`); fuera vuelve al match estricto. Cubre la zona en la que el
# enlace y la vía todavía no se han separado físicamente: la IA conmuta al enlace a
# `TRIGGER_DIST_M` (3.5 m) de él, mucho antes de divergir de verdad. Ajustable.
_LINK_TRANSITION_WINDOW_M = 25.0


def _is_near_link_entry(
    link: RoadLink, my_x: float, my_y: float, window_m: float
) -> bool:
    """¿Estoy a menos de `window_m` del nodo de ENTRADA del enlace (2D)?"""
    if not link.nodes:
        return False
    entry = link.nodes[0]
    return math.hypot(entry.x_m - my_x, entry.y_m - my_y) <= window_m


def _lane_chain_ids(
    mode: FreeroamMode,
    current_link: RoadLink | None,
    next_link: RoadLink | None,
    my_x: float,
    my_y: float,
    window_m: float = _LINK_TRANSITION_WINDOW_M,
) -> set[str]:
    """Ids de vía que, SIN ser `mode.current_id`, cuentan como "mi carril, delante".

    Fase 7 · fix (3). El radar acotaba los candidatos a la geometría de `current_id`,
    pero la topología de la IA cambia ANTES que su posición: `navigation.py` la mete
    en el RoadLink en cuanto está a `TRIGGER_DIST_M` (3.5 m) de él. Resultado: al
    entrar en un enlace dejaba de ver al coche lento que aún tenía delante en la vía
    que deja, y no veía a los que ya circulaban en la de destino. Esto devuelve la
    cadena `from_road → link → to_road` alrededor del cruce:

      - En un **Road** con RoadLink planificado: el enlace SIEMPRE (evita el pileup en
        su entrada) y, solo dentro de la ventana, la vía de **destino** del enlace (así
        frena a tiempo por una cola al otro lado, no al meterse ya en el cruce).
      - Dentro de un **RoadLink**: la vía de **destino** siempre (estamos comprometidos:
        es nuestro carril) y, solo dentro de la ventana, la vía que **dejamos** (donde
        el coche de delante puede seguir de frente sin tomar el enlace).

    La ventana acota el ensanchado a las inmediaciones del cruce: lejos de él el match
    vuelve a ser estricto, así el tráfico de una transversal no provoca frenado
    fantasma. Quien llame filtra luego por producto escalar (que estén DELANTE).
    """
    ids: set[str] = set()

    if mode.current_type == "Road":
        if mode.next_link_id and mode.next_link_type == "RoadLink":
            ids.add(mode.next_link_id)
            if next_link and _is_near_link_entry(next_link, my_x, my_y, window_m):
                ids.add(next_link.to_road_id)

    elif mode.current_type == "RoadLink" and current_link:
        ids.add(current_link.to_road_id)
        if _is_near_link_entry(current_link, my_x, my_y, window_m):
            ids.add(current_link.from_road_id)

    return ids


class _RadarMixin(_MixinBase):
    def _build_vehicle_grid(self) -> None:
        """Construye la rejilla espacial de vehículos del radar (una vez por MCI).

        Indexa por PLID la posición 2D de cada vehículo CON telemetría (IAs y
        jugadores; `players`/`ais` son disjuntos por PLID). El radar la consulta
        para acotar el barrido a un vecindario (O(vecindario)/consulta) en vez de
        recorrer los N vehículos (O(N)/consulta → O(N²) global). `_vehicle_index`
        mapea PLID → (player, is_ai, other_ai), el contexto que el barrido necesita.

        La construye `on_ISP_MCI` antes del bucle de IAs, así todas las IAs del
        paquete comparten la misma foto. Si nunca se llamó (tests que invocan un
        barrido directo), `_vehicle_grid` es None y el radar itera todos los
        vehículos (misma salida) — ver `_iter_radar_candidates`.
        """
        grid = SpatialHashGrid(_VEHICLE_GRID_CELL_M)
        index: dict[int, tuple] = {}
        um = self.user_manager
        if um is not None:
            for p in um.players.values():
                if p.telemetry:
                    c = p.telemetry.coordinates
                    grid.insert_point(p.plid, c.x_m, c.y_m)
                    index[p.plid] = (p, False, None)
            for a in um.ais.values():
                pl = a.player
                if pl.telemetry:
                    c = pl.telemetry.coordinates
                    grid.insert_point(pl.plid, c.x_m, c.y_m)
                    index[pl.plid] = (pl, True, a)
        self._vehicle_grid = grid
        self._vehicle_index = index

    def _iter_radar_candidates(
        self, cx: float, cy: float, radius_m: float
    ) -> Iterator[tuple]:
        """Emite (player, is_ai, other_ai) de los vehículos candidatos alrededor de
        (cx, cy) dentro de `radius_m` (2D).

        Con la rejilla dinámica presente devuelve el SUPERCONJUNTO de vehículos del
        vecindario (la caja contiene el círculo del radio); el barrido llamador
        aplica luego su culling y filtros por-vehículo EXACTOS → salida idéntica a
        recorrer todos. Sin rejilla (None) cae a iterar todos los vehículos en el
        MISMO orden que antes (players, luego ais) — el camino de referencia que la
        red de equivalencia compara contra la rejilla.
        """
        grid = getattr(self, "_vehicle_grid", None)
        if grid is None:
            for p in self.user_manager.players.values():
                yield p, False, None
            for a in self.user_manager.ais.values():
                yield a.player, True, a
            return

        index = self._vehicle_index
        seen: set[int] = set()
        for plid in grid.ids_within(cx, cy, radius_m):
            if plid in seen:
                continue
            seen.add(plid)
            entry = index.get(plid)
            if entry is not None:
                yield entry

    def _scan_lane_ahead(
        self, ai: AI, mode: FreeroamMode, max_dist_m: float
    ) -> list[tuple[float, float, int]]:
        vehicles_ahead = []

        if not ai.player.telemetry:
            return vehicles_ahead

        my_coords = ai.player.telemetry.coordinates
        is_opposing = getattr(mode, "is_driving_opposing", False)

        # =========================================================
        # Geometría actual FUERA del bucle: si no hay una válida, ni iteramos.
        # =========================================================
        if mode.current_type == "Road":
            geom = self.map_recorder.roads.get(mode.current_id)
        elif mode.current_type == "RoadLink":
            geom = self.map_recorder.road_links.get(mode.current_id)
        else:
            geom = None

        if not geom or not geom.nodes:
            return vehicles_ahead

        # =========================================================
        # Constantes direccionales precalculadas: el vector de dirección y la
        # distancia al siguiente nodo se calculan UNA vez antes del bucle.
        # =========================================================
        curr_idx = max(0, min(mode.node_index, len(geom.nodes) - 1))

        # Índices para el vector de dirección (Dot Product) y para la distancia (Empates)
        if is_opposing:
            next_idx_dir = max(0, curr_idx - 1)
            if curr_idx == next_idx_dir:
                next_idx_dir = min(len(geom.nodes) - 1, curr_idx + 1)
            next_idx_dist = max(0, curr_idx - 1)
        else:
            next_idx_dir = min(curr_idx + 1, len(geom.nodes) - 1)
            if curr_idx == next_idx_dir:
                next_idx_dir = max(0, curr_idx - 1)
            next_idx_dist = min(curr_idx + 1, len(geom.nodes) - 1)

        # A. Vector direccional pre-calculado
        node_a = geom.nodes[curr_idx]
        node_b = geom.nodes[next_idx_dir]
        dir_x = node_b.x_m - node_a.x_m
        dir_y = node_b.y_m - node_a.y_m

        # B. Mi distancia al nodo pre-calculada
        target_node = geom.nodes[next_idx_dist]
        mi_dist_al_nodo = math.hypot(
            target_node.x_m - my_coords.x_m, target_node.y_m - my_coords.y_m
        )

        # C. Cadena topológica del cruce (from_road → link → to_road): las vías que,
        # sin ser la mía, cuentan como "mi carril, delante" cerca de un enlace. Se
        # resuelve UNA vez, fuera del bucle (ver `_lane_chain_ids`).
        chain_ids = _lane_chain_ids(
            mode,
            self.map_recorder.road_links.get(mode.current_id)
            if mode.current_type == "RoadLink"
            else None,
            self.map_recorder.road_links.get(mode.next_link_id)
            if mode.next_link_type == "RoadLink" and mode.next_link_id
            else None,
            my_coords.x_m,
            my_coords.y_m,
        )

        # =========================================================
        # 2. ESCANEO Y DETECCIÓN (Bucle Caliente)
        # Los candidatos vienen del vecindario (rejilla espacial) en vez de los N
        # vehículos. El radio de la consulta = el mismo culling de abajo
        # (max_dist + 15), así el conjunto filtrado —y la salida— es idéntico.
        # =========================================================
        for other_player, is_ai, other_ai in self._iter_radar_candidates(
            my_coords.x_m, my_coords.y_m, max_dist_m + 15.0
        ):
            if other_player.plid == ai.player.plid or not other_player.telemetry:
                continue

            other_coords = other_player.telemetry.coordinates

            # Bounding box rápido antes del hypot (culling 2D barato)
            dx = my_coords.x_m - other_coords.x_m
            dy = my_coords.y_m - other_coords.y_m

            if abs(dx) > max_dist_m + 15.0 or abs(dy) > max_dist_m + 15.0:
                continue

            fast_dist = math.hypot(dx, dy)
            if fast_dist > max_dist_m + 15.0:
                continue

            other_road_id = None
            other_node_index = -1

            # ---------------------------------------------------------
            # EXTRACCIÓN TOPOLÓGICA
            # ---------------------------------------------------------
            if is_ai and other_ai and "aic" in other_ai.extra:
                other_mode = other_ai.extra["aic"].active_mode
                if other_mode and other_mode.current_id:
                    other_road_id = other_mode.current_id
                    other_node_index = other_mode.node_index
            else:
                current_time = time.time()
                if len(self._radar_human_cache) > 64:
                    self._radar_human_cache = {
                        plid: d
                        for plid, d in self._radar_human_cache.items()
                        if current_time - d[0] < 10.0
                    }
                cached_data = self._radar_human_cache.get(other_player.plid)

                if not cached_data or (current_time - cached_data[0]) > 0.1:
                    ctx = self.map_recorder.get_location_context(
                        other_coords.x_m, other_coords.y_m, other_coords.z_m
                    )
                    calc_road_id = (
                        ctx.link_id
                        if (ctx.link_id and ctx.link_dist < ctx.road_dist)
                        else ctx.road_id
                    )
                    calc_node_index = -1

                    # Índice exacto del jugador solo si comparte nuestra calle
                    if calc_road_id == mode.current_id:
                        calc_node_index, _ = self._get_closest_node_index(
                            other_coords.x_m, other_coords.y_m, geom.nodes
                        )

                    self._radar_human_cache[other_player.plid] = (
                        current_time,
                        calc_road_id,
                        calc_node_index,
                    )
                    other_road_id = calc_road_id
                    other_node_index = calc_node_index
                else:
                    _, other_road_id, other_node_index = cached_data

            # ---------------------------------------------------------
            # FILTROS ESTRICTOS DE CARRIL
            # ---------------------------------------------------------
            if not other_road_id:
                continue

            same_segment = other_road_id == mode.current_id

            # El otro no va en mi geometría, pero sí en una vía contigua de la cadena
            # del cruce (nuestro próximo enlace, la vía de destino o la que dejamos):
            # cuenta como obstáculo adelante. Evita el pileup en la entrada del enlace
            # y los choques de la transición road↔roadlink (Fase 7 · fix (3)).
            in_lane_chain = not same_segment and other_road_id in chain_ids

            if not same_segment and not in_lane_chain:
                continue

            if same_segment:
                idx_diff = (
                    mode.node_index - other_node_index
                    if is_opposing
                    else other_node_index - mode.node_index
                )

                # Vehículo en nodo inferior = detrás de nosotros → nunca es bloqueante
                if idx_diff < 0:
                    continue

                if idx_diff == 0:
                    su_dist_al_nodo = math.hypot(
                        target_node.x_m - other_coords.x_m,
                        target_node.y_m - other_coords.y_m,
                    )
                    if su_dist_al_nodo > mi_dist_al_nodo:
                        continue
                    if (
                        abs(su_dist_al_nodo - mi_dist_al_nodo) < 0.3
                        and ai.player.plid < other_player.plid
                    ):
                        continue

                elif idx_diff <= 3:
                    vec_x = other_coords.x_m - my_coords.x_m
                    vec_y = other_coords.y_m - my_coords.y_m
                    if (dir_x * vec_x) + (dir_y * vec_y) <= 0:
                        continue
            # in_lane_chain: el otro va por una vía contigua del cruce, donde el
            # node_index no es comparable con el nuestro (geometrías distintas). El
            # único criterio es que esté delante (producto escalar positivo).
            else:
                vec_x = other_coords.x_m - my_coords.x_m
                vec_y = other_coords.y_m - my_coords.y_m
                if (dir_x * vec_x) + (dir_y * vec_y) <= 0:
                    continue

            # ---------------------------------------------------------
            # CÁLCULO DE DISTANCIA FINAL
            # ---------------------------------------------------------
            dist_m = calc_dist_3d(
                my_coords.x_m,
                my_coords.y_m,
                my_coords.z_m,
                other_coords.x_m,
                other_coords.y_m,
                other_coords.z_m,
            )

            if dist_m <= max_dist_m:
                vehicles_ahead.append(
                    (dist_m, other_player.telemetry.speed.speed_kmh, other_player.plid)
                )

        # =========================================================
        # 3. ORDENACIÓN
        # =========================================================
        vehicles_ahead.sort(key=lambda x: x[0])
        return vehicles_ahead

    def _scan_target_lane(
        self, ai: AI, mode: FreeroamMode, target_road_id: str, max_dist_m: float
    ) -> list[tuple[float, float, int]]:
        """
        Escanea un carril específico usando una caché independiente
        para evitar sobreescribir los datos del radar principal.
        """
        vehicles_ahead = []
        if not ai.player.telemetry:
            return vehicles_ahead

        my_coords = ai.player.telemetry.coordinates

        # =========================================================
        # VECTOR DIRECCIONAL BASE (Para saber qué es "hacia adelante")
        # =========================================================
        curr_geom = (
            self.map_recorder.roads.get(mode.current_id)
            or self.map_recorder.road_links.get(mode.current_id)
            or self.map_recorder.lateral_links.get(mode.current_id)
        )
        if not curr_geom or not curr_geom.nodes:
            return []

        curr_idx = min(mode.node_index, len(curr_geom.nodes) - 1)
        next_idx = min(curr_idx + 1, len(curr_geom.nodes) - 1)
        if curr_idx == next_idx:
            curr_idx = max(0, curr_idx - 1)

        my_dir_x = curr_geom.nodes[next_idx].x_m - curr_geom.nodes[curr_idx].x_m
        my_dir_y = curr_geom.nodes[next_idx].y_m - curr_geom.nodes[curr_idx].y_m

        # =========================================================
        # ESCANEO Y DETECCIÓN (Con caché aislada)
        # Candidatos del vecindario (rejilla); radio = culling 2D (max_dist + 15).
        # =========================================================
        for other_player, is_ai, other_ai in self._iter_radar_candidates(
            my_coords.x_m, my_coords.y_m, max_dist_m + 15.0
        ):
            if other_player.plid == ai.player.plid or not other_player.telemetry:
                continue

            other_coords = other_player.telemetry.coordinates

            # Culling espacial rápido 2D
            fast_dist = math.hypot(
                my_coords.x_m - other_coords.x_m, my_coords.y_m - other_coords.y_m
            )
            if fast_dist > max_dist_m + 15.0:
                continue

            # Extracción Topológica
            other_road_id = None
            if is_ai and other_ai and "aic" in other_ai.extra:
                other_mode: FreeroamMode = other_ai.extra["aic"].active_mode
                if other_mode:
                    other_road_id = other_mode.current_id
            else:
                # [!] Usamos una caché propia para este escaner: _target_lane_human_cache
                current_time = time.time()
                if len(self._target_lane_human_cache) > 64:
                    self._target_lane_human_cache = {
                        plid: d
                        for plid, d in self._target_lane_human_cache.items()
                        if current_time - d[0] < 10.0
                    }
                cached_data = self._target_lane_human_cache.get(other_player.plid)

                if not cached_data or (current_time - cached_data[0]) > 0.1:
                    ctx = self.map_recorder.get_location_context(
                        other_coords.x_m, other_coords.y_m, other_coords.z_m
                    )
                    calc_road_id = (
                        ctx.link_id
                        if (ctx.link_id and ctx.link_dist < ctx.road_dist)
                        else ctx.road_id
                    )

                    self._target_lane_human_cache[other_player.plid] = (
                        current_time,
                        calc_road_id,
                    )
                    other_road_id = calc_road_id
                else:
                    # Acceso seguro por índice. El 1 es siempre nuestro calc_road_id
                    other_road_id = cached_data[1]

            # [!] FILTRO ESTRICTO: Solo nos interesa si está en el carril objetivo
            if other_road_id != target_road_id:
                continue

            # [!] FILTRO DIRECCIONAL: ¿Está físicamente delante de nosotros?
            vec_x = other_coords.x_m - my_coords.x_m
            vec_y = other_coords.y_m - my_coords.y_m

            if (my_dir_x * vec_x) + (my_dir_y * vec_y) <= 0:
                continue  # Está detrás

            dist_m = calc_dist_3d(
                my_coords.x_m,
                my_coords.y_m,
                my_coords.z_m,
                other_coords.x_m,
                other_coords.y_m,
                other_coords.z_m,
            )

            if dist_m <= max_dist_m:
                vehicles_ahead.append(
                    (dist_m, other_player.telemetry.speed.speed_kmh, other_player.plid)
                )

        vehicles_ahead.sort(key=lambda x: x[0])
        return vehicles_ahead

    def _scan_return_lane_gap(
        self, ai: "AI", mode: FreeroamMode, max_dist_m: float
    ) -> tuple[float, float]:
        """
        Escanea el carril de retorno desde la posición actual (en el carril rápido).
        Devuelve (dist_más_cercano_delante, dist_más_cercano_detrás) en ese carril.
        """
        if not ai.player.telemetry:
            return 0.0, 0.0

        my_coords = ai.player.telemetry.coordinates
        ret_geom = self.map_recorder.roads.get(mode.overtake_return_lane_id)
        if not ret_geom or not ret_geom.nodes:
            return float("inf"), float("inf")

        closest_idx, _ = self._get_closest_node_index(
            my_coords.x_m, my_coords.y_m, ret_geom.nodes
        )
        next_idx = min(closest_idx + 1, len(ret_geom.nodes) - 1)
        if closest_idx == next_idx:
            next_idx = max(0, closest_idx - 1)
        dir_x = ret_geom.nodes[next_idx].x_m - ret_geom.nodes[closest_idx].x_m
        dir_y = ret_geom.nodes[next_idx].y_m - ret_geom.nodes[closest_idx].y_m

        min_ahead = float("inf")
        min_behind = float("inf")

        # Candidatos del vecindario (rejilla); radio = culling 3D (max_dist * 2),
        # holgado en 2D (dist 2D <= 3D → la caja contiene el conjunto culleado).
        for other_player, is_ai, other_ai in self._iter_radar_candidates(
            my_coords.x_m, my_coords.y_m, max_dist_m * 2.0
        ):
            if other_player.plid == ai.player.plid or not other_player.telemetry:
                continue

            # Filtro topológico: solo coches en el carril de retorno
            if is_ai and other_ai and "aic" in other_ai.extra:
                other_mode = other_ai.extra["aic"].active_mode
                other_road = other_mode.current_road_id if other_mode else None
            else:
                ctx = self.map_recorder.get_location_context(
                    other_player.telemetry.coordinates.x_m,
                    other_player.telemetry.coordinates.y_m,
                    other_player.telemetry.coordinates.z_m,
                )
                other_road = ctx.road_id

            if other_road != mode.overtake_return_lane_id:
                continue

            oc = other_player.telemetry.coordinates
            dist = calc_dist_3d(
                my_coords.x_m, my_coords.y_m, my_coords.z_m, oc.x_m, oc.y_m, oc.z_m
            )
            if dist > max_dist_m * 2.0:
                continue

            dot = dir_x * (oc.x_m - my_coords.x_m) + dir_y * (oc.y_m - my_coords.y_m)

            if dot >= 0:
                min_ahead = min(min_ahead, dist)
            else:
                min_behind = min(min_behind, dist)

        return min_ahead, min_behind
