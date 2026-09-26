# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""独立于求解器的原始附件回算。输出结果是模型证书，不是现场飞行许可。"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import openpyxl
import rasterio
from pyproj import Geod
from rasterio.features import geometry_mask
from rasterio.windows import Window


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "input"
OUT = ROOT / "results" / "solution_certificate.json"
GEOD = Geod(ellps="WGS84")
EPS = 1e-6


def sheet(name: str, tab: str = "数据") -> list[tuple]:
    path = RAW / f"{name}.xlsx"
    return list(openpyxl.load_workbook(path, read_only=True, data_only=True)[tab].values)


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float, name: str, errors: list[str], tol: float = EPS) -> None:
    if not math.isfinite(float(a)) or abs(float(a) - float(b)) > tol:
        errors.append(f"{name}: {a} != {b}")


class Raw:
    def __init__(self) -> None:
        base = json.loads((ROOT / "config/base_parameters.json").read_text(encoding="utf-8"))
        optimization = json.loads((ROOT / "config/optimization_parameters.json").read_text(encoding="utf-8"))
        fixed_conventions = {"terrain_clearance_m": 50, "service_height_m": 30,
                             "gravity_m_s2": 9.81, "charge_soc_break": 0.9,
                             "charge_first_stage_fraction": 0.65,
                             "charge_second_stage_fraction": 0.35, "initial_soc": 1.0}
        for key, expected in fixed_conventions.items():
            if base.get(key) != expected:
                raise ValueError(f"Independent checker convention must be updated for {key}={base.get(key)}")
        if optimization["communication_certificate"]["distance_safety_factor"] != 1.0002:
            raise ValueError("Independent checker distance bound must be updated for current config")
        rows = sheet("调度中心与服务区")
        self.nodes = [rows[2], *rows[6:21]]
        self.node_ids = {row[0]: i for i, row in enumerate(self.nodes)}
        transport = sheet("运输无人机数据")
        names = ("id", "name", "mass", "Q", "V", "vc", "L0", "LF", "E", "rho",
                 "prep", "load", "handoff", "perbox", "vu", "vd", "eta", "downeta")
        self.types = {r[0]: dict(zip(names, r)) for r in transport[2:5]}
        self.units = {g: [r[0] for r in transport[8:16] if r[1] == g] for g in self.types}
        for r in transport[19:22]:
            self.types[r[0]].update(batteries=r[1], charge=r[2])
        self.boxes = []
        for row in sheet("物资需求与配送时限", "逐箱货箱清单")[1:]:
            medical, first = row[2] == "医疗物资", row[5] == "是"
            self.boxes.append(dict(id=row[0], node=self.node_ids[row[1]], mass=row[3], volume=row[4],
                                   medical=medical, first=first, first_deadline=row[6] if first else None,
                                   due=row[7], priority=row[8]))
        relay_rows = sheet("中继无人机数据")
        relay_names = ("id", "name", "airframe_mass", "module_mass", "mass", "vc",
                       "cruise_power", "E", "rho", "prep", "link_setup", "turnaround",
                       "vu", "vd", "eta", "downeta", "hover_power", "comm_power", "max_agl")
        self.relay = dict(zip(relay_names, relay_rows[2]))
        self.relay.update(units=[r[0] for r in relay_rows[6:8]], components=relay_rows[11][1],
                          charge=relay_rows[11][2])
        communication = sheet("通信链路参数")
        self.radio = dict(frequency=communication[2][4], loss=communication[3][4],
                          obstruction=communication[4][4], sensitivity=communication[5][4],
                          fade=communication[6][4], gateway_height=communication[15][4])
        tx = {"transport": (communication[7][4], communication[8][4]),
              "access": (communication[9][4], communication[10][4]),
              "backhaul": (communication[11][4], communication[12][4]),
              "gateway": (communication[13][4], communication[14][4])}
        for kind, left, right in (("direct", "transport", "gateway"),
                                  ("access", "transport", "access"),
                                  ("backhaul", "backhaul", "gateway")):
            a, b = tx[left], tx[right]
            self.radio[kind] = min(a[0] + a[1] + b[1], b[0] + b[1] + a[1]) - (
                self.radio["sensitivity"] + self.radio["fade"] + self.radio["loss"])
        self.dem_path = RAW / "镇龙乡及周边30米DEM.tif"
        with rasterio.open(self.dem_path) as source:
            self.dem = source.read(1)
            self.transform = source.transform
        self.gateway = [self.nodes[0][2], self.nodes[0][3],
                        self.nodes[0][4] + self.radio["gateway_height"]]

    def pixel(self, lon: float, lat: float) -> tuple[float, float]:
        return (~self.transform) * (lon, lat)

    def line_ground(self, a: list[float], b: list[float]) -> tuple[np.ndarray, np.ndarray]:
        """Enumerate every crossed DEM cell by exact grid-boundary parameters."""
        ac, ar = self.pixel(a[0], a[1])
        bc, br = self.pixel(b[0], b[1])
        cuts = [0.0, 1.0]
        for start, end in ((ac, bc), (ar, br)):
            if abs(end - start) > 1e-14:
                cuts.extend((k - start) / (end - start) for k in range(
                    math.floor(min(start, end)) + 1, math.ceil(max(start, end))))
        cuts = np.unique(np.clip(cuts, 0, 1))
        mids = (cuts[:-1] + cuts[1:]) / 2
        columns = np.floor(ac + (bc - ac) * mids).astype(int)
        rows = np.floor(ar + (br - ar) * mids).astype(int)
        if np.any(rows < 0) or np.any(rows >= self.dem.shape[0]) or np.any(columns < 0) or np.any(columns >= self.dem.shape[1]):
            raise ValueError("flight or sight line leaves the DEM")
        return cuts, self.dem[rows, columns]

    def top(self, a: list[float], b: list[float]) -> float:
        return float(np.max(self.line_ground(a, b)[1]))

    def ground(self, a: list[float]) -> float:
        c, r = self.pixel(a[0], a[1])
        return float(self.dem[math.floor(r), math.floor(c)])

    def obstructed(self, a: list[float], b: list[float]) -> bool:
        cuts, elevations = self.line_ground(a, b)
        lowest = np.minimum(a[2] + (b[2] - a[2]) * cuts[:-1],
                            a[2] + (b[2] - a[2]) * cuts[1:])
        return bool(np.any(elevations > lowest + 1e-8))

    def distance(self, a: list[float], b: list[float]) -> float:
        return GEOD.inv(a[0], a[1], b[0], b[1])[2]

    def margin(self, a: list[float], b: list[float], kind: str, blocked: bool,
               safety: float = 1.0) -> float:
        d = math.hypot(self.distance(a, b) * safety, b[2] - a[2]) / 1000
        fspl = 32.45 + 20 * math.log10(self.radio["frequency"]) + 20 * math.log10(max(d, 1e-6))
        return self.radio[kind] - fspl - (self.radio["obstruction"] if blocked else 0)

    def all_sightlines_clear(self, a: list[float], b: list[float], fixed: list[float]) -> bool:
        """A plane through the moving endpoints and provider lower-bounds the whole sight sweep."""
        xy = np.array([a[:2], b[:2], fixed[:2]], dtype=float)
        matrix = np.column_stack((xy, np.ones(3)))
        if abs(np.linalg.det(matrix)) < 1e-14:
            if np.linalg.norm(xy[0] - xy[1]) < 1e-12:
                low = a if a[2] <= b[2] else b
                return not self.obstructed(low, fixed)
            return False
        grad_lon, grad_lat, intercept = np.linalg.solve(matrix, [a[2], b[2], fixed[2]])
        columns, rows = zip(*(self.pixel(*point) for point in xy))
        c0, c1 = max(0, math.floor(min(columns)) - 1), min(self.dem.shape[1], math.ceil(max(columns)) + 1)
        r0, r1 = max(0, math.floor(min(rows)) - 1), min(self.dem.shape[0], math.ceil(max(rows)) + 1)
        if c0 >= c1 or r0 >= r1:
            return False
        local = self.transform * rasterio.Affine.translation(c0, r0)
        polygon = {"type": "Polygon", "coordinates": [[a[:2], b[:2], fixed[:2], a[:2]]]}
        mask = geometry_mask([polygon], out_shape=(r1 - r0, c1 - c0), transform=local,
                             invert=True, all_touched=True)
        rr, cc = np.nonzero(mask)
        if not len(rr):
            return False
        # Minimize the affine altitude plane over all four corners of every touched pixel.
        left = self.transform.c + (c0 + cc) * self.transform.a
        right = left + self.transform.a
        top = self.transform.f + (r0 + rr) * self.transform.e
        bottom = top + self.transform.e
        lower = np.minimum.reduce([grad_lon * lon + grad_lat * lat + intercept
                                   for lon, lat in ((left, top), (left, bottom), (right, top), (right, bottom))])
        return bool(np.all(self.dem[r0 + rr, c0 + cc] <= lower + 1e-8))


def charge_seconds(soc: float, full_charge: float) -> float:
    return full_charge * (0.65 * (0.9 - soc) / 0.9 + 0.35) if soc < 0.9 else full_charge * 0.35 * (1 - soc) / 0.1


def overlaps(intervals: list[tuple[float, float]]) -> bool:
    ordered = sorted(intervals)
    return any(b[0] < a[1] - EPS for a, b in zip(ordered, ordered[1:]))


def audit_q1(raw: Raw, data: dict) -> dict:
    errors: list[str] = []
    coverage = Counter()
    energy_total = time_total = 0.0

    def direct(node: int, kind: str, payload: float, box_count: int) -> tuple[float, float, float]:
        aircraft = raw.types[kind]
        origin, target = raw.nodes[0], raw.nodes[node]
        outward_a = [origin[2], origin[3], origin[4]]
        outward_b = [target[2], target[3], target[4] + 30]
        outward_h = max(raw.top(outward_a, outward_b) + 50, outward_a[2], outward_b[2])
        backward_h = outward_h
        distance = raw.distance(outward_a, outward_b)
        def leg_energy(weight: float, start_height: float, cruise: float) -> float:
            equivalent = aircraft["L0"] - (aircraft["L0"] - aircraft["LF"]) * (weight / aircraft["Q"]) ** 1.5
            return (aircraft["E"] * distance / equivalent +
                    (aircraft["mass"] + weight) * 9.81 * (cruise - start_height) / (aircraft["eta"] * 3.6e6))
        energy = leg_energy(payload, outward_a[2], outward_h) + leg_energy(0, outward_b[2], backward_h)
        flying = ((outward_h - outward_a[2]) / aircraft["vu"] + distance / aircraft["vc"] +
                  (outward_h - outward_b[2]) / aircraft["vd"] +
                  (backward_h - outward_b[2]) / aircraft["vu"] + distance / aircraft["vc"] +
                  (backward_h - outward_a[2]) / aircraft["vd"])
        time = (aircraft["prep"] + aircraft["load"] * box_count + flying +
                aircraft["handoff"] + aircraft["perbox"] * box_count)
        return energy, time, 1 - energy / aircraft["E"]

    for route in data["routes"]:
        kind = route["g"]
        if len(route["order"]) != 1:
            errors.append("Q1 has a multi-stop route")
            continue
        node = route["order"][0]
        ids = route["boxes"]
        coverage.update(ids)
        if any(raw.boxes[i]["node"] != node for i in ids):
            errors.append(f"Q1 wrong destination at S{node:03}")
        payload = sum(raw.boxes[i]["mass"] for i in ids)
        volume = sum(raw.boxes[i]["volume"] for i in ids)
        aircraft = raw.types[kind]
        if payload > aircraft["Q"] + EPS or volume > aircraft["V"] + EPS:
            errors.append(f"Q1 payload/volume at S{node:03}")
        energy, duration, soc = direct(node, kind, payload, len(ids))
        close(energy, route["energy"], f"Q1 S{node:03} energy", errors, 1e-7)
        close(duration, route["duration"], f"Q1 S{node:03} duration", errors)
        close(soc, route["soc"], f"Q1 S{node:03} SOC", errors)
        if soc < aircraft["rho"] / 100 - EPS:
            errors.append(f"Q1 SOC at S{node:03}")
        energy_total += energy
        time_total += duration
    if coverage != Counter(range(len(raw.boxes))):
        errors.append("Q1 box coverage / uniqueness")
    if len(data["capacities"]) != 45:
        errors.append("Q1 missing safe capacity values")
    for entry in data["capacities"]:
        node, kind = entry["node"], entry["g"]
        aircraft = raw.types[kind]
        low, high = 0.0, aircraft["Q"]
        for _ in range(55):
            mid = (low + high) / 2
            if direct(node, kind, mid, 0)[0] <= aircraft["E"] * (1 - aircraft["rho"] / 100):
                low = mid
            else:
                high = mid
        close(low, entry["maxload"], f"Q1 S{node:03} {kind} safe capacity", errors, 1e-5)
    close(energy_total, data["summary"]["energy"], "Q1 total energy", errors, 1e-6)
    close(time_total, data["summary"]["time"], "Q1 total duration", errors, 1e-6)
    return dict(pass_=not errors, errors=errors, box_count=sum(coverage.values()),
                route_count=len(data["routes"]), capacity_count=len(data["capacities"]),
                energy_kwh=energy_total, total_route_duration_s=time_total)


def audit_transport(raw: Raw, name: str, data: dict) -> dict:
    errors: list[str] = []
    all_boxes: list[int] = []
    unit_occupancy: dict[str, list[tuple[float, float]]] = defaultdict(list)
    battery_occupancy: dict[str, list[tuple[float, float]]] = defaultdict(list)
    deliveries: dict[int, float] = {}
    segment_times: dict[str, list[tuple[dict, float, float]]] = {}
    energy_rows = []
    for route in data["routes"]:
        ident, kind = route["id"], route["g"]
        aircraft = raw.types[kind]
        assigned = route["boxes"]
        all_boxes.extend(assigned)
        if len(set(assigned)) != len(assigned) or not assigned or any(i < 0 or i >= len(raw.boxes) for i in assigned):
            errors.append(f"{ident}: invalid box indices")
            continue
        order = route["order"]
        if len(set(order)) != len(order) or set(order) != {raw.boxes[i]["node"] for i in assigned}:
            errors.append(f"{ident}: wrong destination or duplicate stop")
            continue
        payload = sum(raw.boxes[i]["mass"] for i in assigned)
        volume = sum(raw.boxes[i]["volume"] for i in assigned)
        if payload > aircraft["Q"] + EPS or volume > aircraft["V"] + EPS:
            errors.append(f"{ident}: payload or volume")
        close(payload, route["w"], f"{ident} mass", errors)
        close(volume, route["v"], f"{ident} volume", errors)
        clock = aircraft["prep"] + aircraft["load"] * len(assigned)
        close(clock, route["takeoff"], f"{ident} takeoff", errors)
        segment_expected = []
        remaining, previous = payload, 0
        horizontal = climb = 0.0
        expected_deliveries = {}
        for node in [*order, 0]:
            start_node, end_node = raw.nodes[previous], raw.nodes[node]
            a = [start_node[2], start_node[3], start_node[4] + (30 if previous else 0)]
            b = [end_node[2], end_node[3], end_node[4] + (30 if node else 0)]
            cruise_height = max(raw.top(a, b) + 50, a[2], b[2])
            distance = raw.distance(a, b)
            up, across, down = ((cruise_height - a[2]) / aircraft["vu"],
                                distance / aircraft["vc"], (cruise_height - b[2]) / aircraft["vd"])
            for phase, duration, start_pos, end_pos in (("爬升", up, a, [a[0], a[1], cruise_height]),
                                                        ("巡航", across, [a[0], a[1], cruise_height], [b[0], b[1], cruise_height]),
                                                        ("下降", down, [b[0], b[1], cruise_height], b)):
                segment_expected.append((phase, clock, clock + duration, start_pos, end_pos))
                clock += duration
            equivalent_range = aircraft["L0"] - (aircraft["L0"] - aircraft["LF"]) * (remaining / aircraft["Q"]) ** 1.5
            horizontal += aircraft["E"] * distance / equivalent_range
            climb += (aircraft["mass"] + remaining) * 9.81 * (cruise_height - a[2]) / (aircraft["eta"] * 3.6e6)
            if node:
                here = [i for i in assigned if raw.boxes[i]["node"] == node]
                handoff = aircraft["handoff"] + aircraft["perbox"] * len(here)
                segment_expected.append(("交接", clock, clock + handoff, b, b))
                clock += handoff
                for i in here:
                    expected_deliveries[i] = route["start"] + clock
                remaining -= sum(raw.boxes[i]["mass"] for i in here)
            previous = node
        energy = horizontal + climb
        soc = 1 - energy / aircraft["E"]
        close(energy, route["energy"], f"{ident} energy", errors, 1e-7)
        close(soc, route["soc"], f"{ident} SOC", errors, 1e-7)
        close(clock, route["duration"], f"{ident} duration", errors)
        close(route["start"] + clock, route["end"], f"{ident} end", errors)
        if soc < aircraft["rho"] / 100 - EPS:
            errors.append(f"{ident}: return SOC below reserve")
        if len(route["segments"]) != len(segment_expected):
            errors.append(f"{ident}: segment count")
        else:
            for i, (stored, expected) in enumerate(zip(route["segments"], segment_expected)):
                phase, start, end, a, b = expected
                if stored["phase"] != phase:
                    errors.append(f"{ident}: phase {i}")
                close(stored["start"], start, f"{ident} segment {i} start", errors)
                close(stored["end"], end, f"{ident} segment {i} end", errors)
                for key, point in (("a", a), ("b", b)):
                    for coordinate, actual in zip(stored[key], point):
                        close(coordinate, actual, f"{ident} segment {i} {key}", errors)
        segment_times[ident] = [(s, route["start"] + s["start"], route["start"] + s["end"])
                                for s in route["segments"]]
        if {int(i) for i in route["deliver"]} != set(expected_deliveries):
            errors.append(f"{ident}: delivery set")
        for i, when in expected_deliveries.items():
            close(route["start"] + route["deliver"][str(i)], when, f"{ident} box {i} time", errors)
            deliveries[i] = when
        if route["unit"] not in raw.units[kind]:
            errors.append(f"{ident}: unknown transport unit")
        if route["battery"] not in [f"{kind}B{i:02}" for i in range(1, aircraft["batteries"] + 1)]:
            errors.append(f"{ident}: unknown battery")
        unit_occupancy[route["unit"]].append((route["start"], route["end"]))
        battery_occupancy[route["battery"]].append((route["start"], route["end"] + charge_seconds(soc, aircraft["charge"])))
        energy_rows.append(dict(id=ident, kind=kind, horizontal_kwh=horizontal, climb_kwh=climb,
                                energy_kwh=energy, reserve_kwh=aircraft["E"] * (1 - aircraft["rho"] / 100),
                                soc=soc))
    if Counter(all_boxes) != Counter(range(len(raw.boxes))):
        errors.append(f"{name}: box coverage / uniqueness")
    for ident, intervals in [*unit_occupancy.items(), *battery_occupancy.items()]:
        if overlaps(intervals):
            errors.append(f"{name}: resource overlap {ident}")
    hard_slacks, medical_slacks, first_slacks = [], [], []
    tardiness = 0.0
    for i, box in enumerate(raw.boxes):
        if i not in deliveries:
            continue
        time = deliveries[i]
        if box["medical"]:
            medical_slacks.append(box["due"] - time)
            hard_slacks.append(box["due"] - time)
        if box["first"]:
            first_slacks.append(box["first_deadline"] - time)
            hard_slacks.append(box["first_deadline"] - time)
        if not box["medical"]:
            tardiness += box["priority"] * max(0, time - box["due"])
    if hard_slacks and min(hard_slacks) < -EPS:
        errors.append(f"{name}: hard deadline violation")
    summary = data["summary"]
    close(sum(row["energy_kwh"] for row in energy_rows) +
          (sum(r["energy"] for r in data.get("relays", []))), summary["energy"], f"{name} total energy", errors, 1e-6)
    close(max(r["end"] for r in data["routes"] + data.get("relays", [])), summary["makespan"], f"{name} makespan", errors)
    close(tardiness, summary["weighted_tardiness"], f"{name} soft tardiness", errors)
    return dict(pass_=not errors, errors=errors, route_count=len(data["routes"]), box_count=len(deliveries),
                medical_count=len(medical_slacks), first_count=len(first_slacks),
                hard_box_count=sum(b["medical"] or b["first"] for b in raw.boxes),
                min_hard_slack_s=min(hard_slacks), weighted_soft_tardiness_s=tardiness,
                min_transport_soc=min(row["soc"] for row in energy_rows), energy_breakdown=energy_rows,
                segment_times=segment_times)


def audit_relay(raw: Raw, data: dict) -> dict:
    errors: list[str] = []
    unit_intervals: dict[str, list[tuple[float, float]]] = defaultdict(list)
    component_intervals: dict[str, list[tuple[float, float]]] = defaultdict(list)
    margins = []
    t = raw.relay
    origin = [raw.nodes[0][2], raw.nodes[0][3], raw.nodes[0][4]]
    for r in data["relays"]:
        ident, point = r["id"], r["pos"]
        max_height = max(raw.top(origin, point) + 50, point[2])
        distance = raw.distance(origin, point)
        outward = (max_height - origin[2]) / t["vu"] + distance / t["vc"] + (max_height - point[2]) / t["vd"]
        return_time = (max_height - point[2]) / t["vu"] + distance / t["vc"] + (max_height - origin[2]) / t["vd"]
        ready = r["start"] + t["prep"] + outward + t["link_setup"]
        close(ready, r["ready"], f"{ident} ready", errors)
        close(r["service_end"] + return_time, r["end"], f"{ident} end", errors)
        energy = (2 * t["cruise_power"] * distance / t["vc"] / 3600 +
                  t["mass"] * 9.81 * ((max_height - origin[2]) + (max_height - point[2])) /
                  (t["eta"] * 3.6e6) +
                  (r["service_end"] - r["ready"] + t["link_setup"]) *
                  (t["hover_power"] + t["comm_power"]) / 3600)
        soc = 1 - energy / t["E"]
        close(energy, r["energy"], f"{ident} energy", errors, 1e-6)
        close(soc, r["soc"], f"{ident} SOC", errors, 1e-6)
        if soc < t["rho"] / 100 - EPS or r["service_end"] < ready - EPS:
            errors.append(f"{ident}: energy reserve / negative service")
        if point[2] - raw.ground(point) > t["max_agl"] + EPS:
            errors.append(f"{ident}: altitude above limit")
        if r["unit"] not in t["units"] or r["component"] not in [f"RB{i:02}" for i in range(1, t["components"] + 1)]:
            errors.append(f"{ident}: unknown relay resource")
        unit_intervals[r["unit"]].append((r["start"], r["end"] + t["turnaround"]))
        component_intervals[r["component"]].append((r["start"], r["end"] + charge_seconds(soc, t["charge"])))
        margin = raw.margin(point, raw.gateway, "backhaul", raw.obstructed(point, raw.gateway))
        margins.append(margin)
        if margin < -EPS:
            errors.append(f"{ident}: backhaul unavailable")
    for ident, intervals in [*unit_intervals.items(), *component_intervals.items()]:
        if overlaps(intervals):
            errors.append(f"relay resource overlap {ident}")
    return dict(pass_=not errors, errors=errors, relay_count=len(data["relays"]),
                min_relay_soc=min(r["soc"] for r in data["relays"]),
                min_backhaul_margin_db=min(margins))


def audit_communications(raw: Raw, data: dict, segments: dict) -> dict:
    errors: list[str] = []
    by_route = defaultdict(list)
    relay_by_id = {r["id"]: r for r in data["relays"]}
    for record in data["communication"]:
        by_route[record["route"]].append(record)
    min_margin = math.inf
    methods = Counter()
    margin_rows = []
    for route in data["routes"]:
        ident = route["id"]
        records = sorted(by_route[ident], key=lambda row: row["start"])
        cursor = route["start"] + route["takeoff"]
        for record in records:
            start, end = record["start"], record["end"]
            if abs(start - cursor) > EPS or end <= start:
                errors.append(f"{ident}: communication gap or reversed interval at {start}")
            cursor = end
            matches = [(s, a, b) for s, a, b in segments[ident] if a - EPS <= start and end <= b + EPS]
            if len(matches) != 1:
                errors.append(f"{ident}: interval crosses a physical segment {start}")
                continue
            segment, a, b = matches[0]
            if segment["phase"] != record["phase"]:
                errors.append(f"{ident}: communication phase mismatch {start}")
            def position(instant: float) -> list[float]:
                fraction = (instant - a) / (b - a)
                return [x + (y - x) * fraction for x, y in zip(segment["a"], segment["b"])]
            p, q = position(start), position(end)
            if record["provider"] == "G01":
                fixed, kind = raw.gateway, "direct"
                if record["relay_task"] is not None:
                    errors.append(f"{ident}: direct record has relay task")
            else:
                relay = relay_by_id.get(record["relay_task"])
                if relay is None or relay["unit"] != record["provider"]:
                    errors.append(f"{ident}: invalid relay provider {start}")
                    continue
                if start < relay["ready"] - EPS or end > relay["service_end"] + EPS:
                    errors.append(f"{ident}: relay inactive {start}")
                fixed, kind = relay["pos"], "access"
            # The maximum distance of a point moving linearly to a fixed point is at an endpoint.
            margin_worst = min(raw.margin(p, fixed, kind, True, 1.0002),
                               raw.margin(q, fixed, kind, True, 1.0002))
            if margin_worst >= -EPS:
                margin, method = margin_worst, "worst_obstruction"
            elif raw.all_sightlines_clear(p, q, fixed):
                margin = min(raw.margin(p, fixed, kind, False, 1.0002),
                             raw.margin(q, fixed, kind, False, 1.0002))
                method = "continuous_LOS"
            else:
                margin, method = margin_worst, "unproven"
            methods[method] += 1
            min_margin = min(min_margin, margin)
            margin_rows.append(dict(route=ident, start_s=start, end_s=end,
                                    provider=record["provider"], method=method,
                                    margin_db=margin))
            if margin < -EPS:
                errors.append(f"{ident}: uncertified link {start:.3f}-{end:.3f}, margin {margin:.3f}")
        if abs(cursor - route["end"]) > EPS:
            errors.append(f"{ident}: incomplete communication coverage")
    return dict(pass_=not errors, errors=errors[:100], total_errors=len(errors),
                interval_count=len(data["communication"]), min_continuous_margin_db=min_margin,
                methods=dict(methods), intervals=margin_rows)


def dense_tightest(raw: Raw, data: dict, segments: dict, time_step: float = 0.1,
                   sight_step_m: float = 1.0) -> dict:
    """Independent dense diagnostic; sampling is not a proof of continuity."""
    record = min(data["communication"], key=lambda row: row["margin"])
    route = record["route"]
    segment, a, b = next((s, a, b) for s, a, b in segments[route]
                         if a - EPS <= record["start"] and record["end"] <= b + EPS)
    relay = next((r for r in data["relays"] if r["id"] == record["relay_task"]), None)
    fixed = raw.gateway if record["provider"] == "G01" else relay["pos"]
    kind = "direct" if relay is None else "access"
    times = np.linspace(record["start"], record["end"],
                        math.ceil((record["end"] - record["start"]) / time_step) + 1)
    minimum, worst_time, obstruction_count = math.inf, None, 0
    for instant in times:
        f = (instant - a) / (b - a)
        point = [x + f * (y - x) for x, y in zip(segment["a"], segment["b"])]
        d = raw.distance(point, fixed)
        steps = max(1, math.ceil(d / sight_step_m))
        fractions = np.linspace(0, 1, steps + 1)
        longitude = point[0] + fractions * (fixed[0] - point[0])
        latitude = point[1] + fractions * (fixed[1] - point[1])
        c, r = raw.pixel(longitude, latitude)
        rr, cc = np.floor(r).astype(int), np.floor(c).astype(int)
        if np.any(rr < 0) or np.any(cc < 0) or np.any(rr >= raw.dem.shape[0]) or np.any(cc >= raw.dem.shape[1]):
            raise ValueError("tightest sightline leaves DEM")
        sight_height = point[2] + fractions * (fixed[2] - point[2])
        blocked = bool(np.any(raw.dem[rr, cc] > sight_height + 1e-8))
        obstruction_count += blocked
        margin = raw.margin(point, fixed, kind, blocked)
        if margin < minimum:
            minimum, worst_time = margin, float(instant)
    return dict(route=route, provider=record["provider"], start_s=record["start"],
                end_s=record["end"], samples=len(times), time_step_max_s=float(np.max(np.diff(times))),
                sight_step_max_m=sight_step_m, obstructed_samples=obstruction_count,
                min_sampled_actual_margin_db=minimum, worst_time_s=worst_time,
                archived_proof_margin_db=record["margin"])


def main() -> int:
    raw = Raw()
    if len(raw.boxes) != 80 or sum(b["mass"] for b in raw.boxes) != 758:
        raise ValueError("raw manifest does not match the 80-box, 758-kg task")
    q1 = json.loads((ROOT / "results/q1_rho20.json").read_text())
    q2 = json.loads((ROOT / "results/q2.json").read_text())
    q3 = json.loads((ROOT / "results/q3.json").read_text())
    first = audit_q1(raw, q1)
    second = audit_transport(raw, "q2", q2)
    third = audit_transport(raw, "q3", q3)
    relays = audit_relay(raw, q3)
    links = audit_communications(raw, q3, third["segment_times"])
    tight = dense_tightest(raw, q3, third["segment_times"])
    for result in (second, third):
        result.pop("segment_times")
    paths = [*sorted(RAW.glob("*.xlsx")), raw.dem_path,
             ROOT / "config/base_parameters.json", ROOT / "config/optimization_parameters.json",
             ROOT / "results/q1_rho20.json", ROOT / "results/q2.json", ROOT / "results/q3.json"]
    output = dict(status="PASS" if all(x["pass_"] for x in (first, second, third, relays, links))
                  and tight["min_sampled_actual_margin_db"] >= -EPS else "FAIL",
                  scope="independent raw-input replay of selected Q1/Q2/Q3; dense T021a check is diagnostic",
                  inputs={str(p.relative_to(ROOT)): fingerprint(p) for p in paths},
                  q1=first, q2=second, q3=third, relay=relays, communication=links, tightest_dense=tight)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": output["status"], "q1_errors": len(first["errors"]), "q2_errors": len(second["errors"]),
                      "q3_errors": len(third["errors"]), "relay_errors": len(relays["errors"]),
                      "link_errors": links["total_errors"], "dense": tight}, ensure_ascii=False, indent=2))
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
