"""
Module F: Visual Primitive Codec

Encodes model outputs into structured visual primitives (ref + box/point)
with associated token entropy, and decodes aggregated primitives back
into model-consumable format.

Design inspired by DeepSeek-AI "Thinking with Visual Primitives" (2025):
    <ref>TARGET</ref><box>[[x1,y1,x2,y2],...]</box>
    <ref>TARGET</ref><point>[[x,y],...]</point>

Privacy guarantee: only structured primitives + entropy are transmitted,
never raw images or raw gradients.

Pure NumPy implementation. No PyTorch dependency. Streamlit Cloud compatible.
"""
from __future__ import annotations

import numpy as np
import json
import hashlib
import re
from typing import List, Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum


class PrimitiveType(Enum):
    """Type of visual primitive."""
    BOX = "box"       # Bounding box: [[x1,y1,x2,y2], ...]
    POINT = "point"   # Point coordinate: [[x,y], ...]
    PATH = "path"     # Ordered point sequence: [[x1,y1],[x2,y2],...]


@dataclass
class VisualPrimitive:
    """A single visual primitive with confidence metadata.

    Attributes:
        ref: Semantic label (e.g., "healthy organoid", "obstacle at door")
        primitive_type: BOX, POINT, or PATH
        coords: Normalized coordinates (0-999 integers)
            - BOX: [[x1,y1,x2,y2], ...]  (top-left, bottom-right)
            - POINT: [[x,y], ...]
            - PATH: [[x1,y1],[x2,y2],...]
        token_entropy: Shannon entropy of the token distribution at this output.
            Low entropy = high confidence, high entropy = uncertain.
        source_client: Client ID that produced this primitive.
        image_hash: SHA-256 hash of the source image (for dedup, not the image itself).
        auxiliary: Optional metadata (area, circularity, class_id, etc.)
    """
    ref: str
    primitive_type: PrimitiveType
    coords: List[List[int]]
    token_entropy: float
    source_client: str = ""
    image_hash: str = ""
    auxiliary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "ref": self.ref,
            "type": self.primitive_type.value,
            "coords": self.coords,
            "entropy": round(self.token_entropy, 6),
            "client": self.source_client,
            "img_hash": self.image_hash[:12],  # truncated for bandwidth
            "aux": self.auxiliary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "VisualPrimitive":
        """Deserialize from dictionary."""
        return cls(
            ref=d["ref"],
            primitive_type=PrimitiveType(d["type"]),
            coords=d["coords"],
            token_entropy=d["entropy"],
            source_client=d.get("client", ""),
            image_hash=d.get("img_hash", ""),
            auxiliary=d.get("aux", {}),
        )

    def __repr__(self) -> str:
        n = len(self.coords)
        return (f"Primitive({self.ref!r}, {self.primitive_type.value}, "
                f"{n} items, H={self.token_entropy:.3f})")


@dataclass
class PrimitiveBatch:
    """A batch of visual primitives from one client for one FL round.

    This is the unit of communication between client and server.
    """
    client_id: str
    round_id: int
    primitives: List[VisualPrimitive] = field(default_factory=list)
    timestamp: float = 0.0

    def to_json(self) -> str:
        """Serialize to JSON string."""
        payload = {
            "client_id": self.client_id,
            "round_id": self.round_id,
            "timestamp": self.timestamp,
            "primitives": [p.to_dict() for p in self.primitives],
        }
        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "PrimitiveBatch":
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        primitives = [VisualPrimitive.from_dict(p) for p in data["primitives"]]
        return cls(
            client_id=data["client_id"],
            round_id=data["round_id"],
            primitives=primitives,
            timestamp=data.get("timestamp", 0.0),
        )

    def size_bytes(self) -> int:
        """Approximate serialized size in bytes."""
        return len(self.to_json().encode("utf-8"))

    def summary(self) -> dict:
        """Batch-level statistics."""
        if not self.primitives:
            return {"count": 0, "avg_entropy": 0.0, "types": {}}

        entropies = [p.token_entropy for p in self.primitives]
        type_counts = {}
        for p in self.primitives:
            t = p.primitive_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "count": len(self.primitives),
            "avg_entropy": round(float(np.mean(entropies)), 4),
            "min_entropy": round(float(np.min(entropies)), 4),
            "max_entropy": round(float(np.max(entropies)), 4),
            "std_entropy": round(float(np.std(entropies)), 4),
            "types": type_counts,
            "size_bytes": self.size_bytes(),
        }


class PrimitiveCodec:
    """Encoder/decoder for visual primitives.

    Client-side usage:
        codec = PrimitiveCodec(client_id="lab_A")
        batch = codec.encode_detections(detections, image_array, round_id=1)

    Server-side usage:
        codec = PrimitiveCodec()
        primitives = codec.decode_batch(json_str)
    """

    def __init__(self, client_id: str = ""):
        self.client_id = client_id

    # ── Encoding ──────────────────────────────────────────────

    @staticmethod
    def compute_image_hash(image: np.ndarray) -> str:
        """Compute SHA-256 hash of image for deduplication.

        Args:
            image: numpy array (H, W, C) or (H, W)
        """
        # Use a small hash of the image shape + first/last 100 pixels
        flat = image.flatten()
        fingerprint = np.concatenate([flat[:100], flat[-100:]])
        return hashlib.sha256(fingerprint.tobytes()).hexdigest()

    @staticmethod
    def normalize_bbox(
        x1: float, y1: float, x2: float, y2: float,
        img_w: int, img_h: int,
    ) -> List[int]:
        """Normalize bbox to 0-999 integer coordinates.

        Args:
            x1, y1, x2, y2: pixel coordinates
            img_w, img_h: image dimensions
        """
        nx1 = int(np.clip(x1 / img_w * 999, 0, 999))
        ny1 = int(np.clip(y1 / img_h * 999, 0, 999))
        nx2 = int(np.clip(x2 / img_w * 999, 0, 999))
        ny2 = int(np.clip(y2 / img_h * 999, 0, 999))
        return [nx1, ny1, nx2, ny2]

    @staticmethod
    def normalize_point(x: float, y: float, img_w: int, img_h: int) -> List[int]:
        """Normalize point to 0-999 integer coordinates."""
        nx = int(np.clip(x / img_w * 999, 0, 999))
        ny = int(np.clip(y / img_h * 999, 0, 999))
        return [nx, ny]

    @staticmethod
    def compute_token_entropy(logits: np.ndarray) -> float:
        """Compute Shannon entropy from logits.

        Args:
            logits: 1D array of raw logit scores for a token position.

        Returns:
            Shannon entropy H = -sum(p * log(p)), where p = softmax(logits).
        """
        if logits is None or len(logits) == 0:
            return 0.0

        # Numerically stable softmax
        logits_shifted = logits - np.max(logits)
        exp_logits = np.exp(logits_shifted)
        probs = exp_logits / np.sum(exp_logits)

        # Filter out near-zero probs to avoid log(0)
        probs = probs[probs > 1e-10]
        entropy = -np.sum(probs * np.log(probs))
        return float(entropy)

    def encode_detections(
        self,
        detections: list,
        image: Optional[np.ndarray] = None,
        round_id: int = 0,
        img_w: int = 640,
        img_h: int = 640,
    ) -> PrimitiveBatch:
        """Encode detection results into visual primitives.

        Compatible with YOLO Detection objects from organoid-fl/detector.py.

        Args:
            detections: list of objects with attributes:
                - bbox: [x1, y1, x2, y2]
                - class_name: str
                - confidence: float
                - area: float (optional)
                - width, height: float (optional)
            image: source image array (for hash computation)
            round_id: FL round number
            img_w, img_h: image dimensions for coordinate normalization

        Returns:
            PrimitiveBatch ready for transmission to server.
        """
        img_hash = ""
        if image is not None:
            img_hash = self.compute_image_hash(image)

        primitives = []
        for det in detections:
            bbox = det.bbox if hasattr(det, "bbox") else det.get("bbox", [0, 0, 0, 0])
            class_name = det.class_name if hasattr(det, "class_name") else det.get("class_name", "unknown")
            conf = det.confidence if hasattr(det, "confidence") else det.get("confidence", 0.5)

            # Normalize coordinates
            coords = self.normalize_bbox(bbox[0], bbox[1], bbox[2], bbox[3], img_w, img_h)

            # Use detection confidence as proxy for token entropy
            # (low confidence → high entropy, high confidence → low entropy)
            # H = -log(conf) maps conf∈[0,1] to H∈[0, +inf)
            token_entropy = -np.log(max(conf, 1e-10))

            # Collect auxiliary metadata
            aux = {}
            if hasattr(det, "area"):
                aux["area"] = det.area
            if hasattr(det, "width") and hasattr(det, "height"):
                aux["aspect_ratio"] = round(det.width / max(det.height, 1e-6), 3)
            if hasattr(det, "class_id"):
                aux["class_id"] = det.class_id

            primitives.append(VisualPrimitive(
                ref=class_name,
                primitive_type=PrimitiveType.BOX,
                coords=[coords],
                token_entropy=token_entropy,
                source_client=self.client_id,
                image_hash=img_hash,
                auxiliary=aux,
            ))

        return PrimitiveBatch(
            client_id=self.client_id,
            round_id=round_id,
            primitives=primitives,
            timestamp=np.datetime64("now").astype(float) if hasattr(np, "datetime64") else 0.0,
        )

    def encode_points(
        self,
        points: List[Tuple[float, float]],
        labels: List[str],
        entropies: Optional[List[float]] = None,
        image: Optional[np.ndarray] = None,
        round_id: int = 0,
        img_w: int = 640,
        img_h: int = 640,
    ) -> PrimitiveBatch:
        """Encode point annotations into visual primitives.

        For embodied-fl: obstacle locations, grasp points, navigation waypoints.

        Args:
            points: list of (x, y) pixel coordinates
            labels: semantic label for each point
            entropies: optional entropy per point (default 1.0 = maximum uncertainty)
            image: source image array
            round_id: FL round number
            img_w, img_h: image dimensions

        Returns:
            PrimitiveBatch
        """
        img_hash = ""
        if image is not None:
            img_hash = self.compute_image_hash(image)

        if entropies is None:
            entropies = [1.0] * len(points)

        primitives = []
        for (x, y), label, ent in zip(points, labels, entropies):
            coords = self.normalize_point(x, y, img_w, img_h)
            primitives.append(VisualPrimitive(
                ref=label,
                primitive_type=PrimitiveType.POINT,
                coords=[coords],
                token_entropy=ent,
                source_client=self.client_id,
                image_hash=img_hash,
            ))

        return PrimitiveBatch(
            client_id=self.client_id,
            round_id=round_id,
            primitives=primitives,
        )

    def encode_paths(
        self,
        paths: List[List[Tuple[float, float]]],
        labels: List[str],
        entropies: Optional[List[float]] = None,
        image: Optional[np.ndarray] = None,
        round_id: int = 0,
        img_w: int = 640,
        img_h: int = 640,
    ) -> PrimitiveBatch:
        """Encode path sequences into visual primitives.

        For embodied-fl: robot trajectories, navigation routes.

        Args:
            paths: list of paths, each path is a list of (x, y) waypoints
            labels: semantic label for each path
            entropies: optional entropy per path
            image: source image array
            round_id: FL round number
            img_w, img_h: image dimensions

        Returns:
            PrimitiveBatch
        """
        img_hash = ""
        if image is not None:
            img_hash = self.compute_image_hash(image)

        if entropies is None:
            entropies = [1.0] * len(paths)

        primitives = []
        for path, label, ent in zip(paths, labels, entropies):
            coords = [self.normalize_point(x, y, img_w, img_h) for x, y in path]
            primitives.append(VisualPrimitive(
                ref=label,
                primitive_type=PrimitiveType.PATH,
                coords=coords,
                token_entropy=ent,
                source_client=self.client_id,
                image_hash=img_hash,
            ))

        return PrimitiveBatch(
            client_id=self.client_id,
            round_id=round_id,
            primitives=primitives,
        )

    # ── Decoding ──────────────────────────────────────────────

    @staticmethod
    def decode_batch(json_str: str) -> PrimitiveBatch:
        """Decode a JSON-encoded PrimitiveBatch from client.

        Server-side usage.
        """
        return PrimitiveBatch.from_json(json_str)

    @staticmethod
    def decode_multiple(batches_json: List[str]) -> List[PrimitiveBatch]:
        """Decode multiple PrimitiveBatch JSON strings.

        Args:
            batches_json: list of JSON strings from different clients.

        Returns:
            List of PrimitiveBatch objects.
        """
        return [PrimitiveBatch.from_json(j) for j in batches_json]

    # ── Coordinate Alignment ──────────────────────────────────

    @staticmethod
    def align_coordinates(
        primitives: List[VisualPrimitive],
        src_w: int, src_h: int,
        dst_w: int, dst_h: int,
    ) -> List[VisualPrimitive]:
        """Re-normalize coordinates from one image size to another.

        Useful when clients have different image resolutions.
        """
        aligned = []
        for p in primitives:
            new_coords = []
            for coord in p.coords:
                if p.primitive_type == PrimitiveType.BOX and len(coord) == 4:
                    x1 = int(coord[0] / 999 * dst_w)
                    y1 = int(coord[1] / 999 * dst_h)
                    x2 = int(coord[2] / 999 * dst_w)
                    y2 = int(coord[3] / 999 * dst_h)
                    new_coords.append([x1, y1, x2, y2])
                elif p.primitive_type in (PrimitiveType.POINT, PrimitiveType.PATH) and len(coord) == 2:
                    x = int(coord[0] / 999 * dst_w)
                    y = int(coord[1] / 999 * dst_h)
                    new_coords.append([x, y])
            aligned.append(VisualPrimitive(
                ref=p.ref,
                primitive_type=p.primitive_type,
                coords=new_coords,
                token_entropy=p.token_entropy,
                source_client=p.source_client,
                image_hash=p.image_hash,
                auxiliary=p.auxiliary,
            ))
        return aligned

    # ── Format Conversion ─────────────────────────────────────

    @staticmethod
    def to_deepseek_format(primitives: List[VisualPrimitive]) -> str:
        """Convert primitives to DeepSeek-style special token format.

        Output example:
            <|ref|>healthy organoid<|/ref|><|box|>[[120,340,450,670]]<|/box|>
            <|ref|>obstacle<|/ref|><|point|>[[234,567]]<|/point|>
        """
        parts = []
        for p in primitives:
            ref_part = f"<|ref|>{p.ref}<|/ref|>"
            if p.primitive_type == PrimitiveType.BOX:
                coord_str = ",".join(str(c) for c in p.coords[0])
                parts.append(f"{ref_part}<|box|>[[{coord_str}]]<|/box|>")
            elif p.primitive_type == PrimitiveType.POINT:
                coord_str = ",".join(str(c) for c in p.coords[0])
                parts.append(f"{ref_part}<|point|>[[{coord_str}]]<|/point|>")
            elif p.primitive_type == PrimitiveType.PATH:
                coord_str = "],[".join(",".join(str(c) for c in pt) for pt in p.coords)
                parts.append(f"{ref_part}<|path|>[[{coord_str}]]<|/path|>")
        return "\n".join(parts)

    @staticmethod
    def parse_deepseek_format(text: str) -> List[VisualPrimitive]:
        """Parse DeepSeek-style special token format back into primitives.

        Supports <box>, <point>, and <path> tags.
        """
        primitives = []

        # Pattern: <|ref|>label<|/ref|><|type|>[[coords]]<|/type|>
        pattern = r"<\|ref\|>(.*?)<\|/ref\|><\|(box|point|path)\|>\[\[(.*?)\]\]<\|/\2\|>"
        for match in re.finditer(pattern, text, re.DOTALL):
            ref = match.group(1).strip()
            ptype = match.group(2)
            coord_str = match.group(3).strip()

            # Parse coordinates
            coords = []
            for group in coord_str.split("],["):
                group = group.strip("[] ")
                nums = [int(x.strip()) for x in group.split(",")]
                coords.append(nums)

            type_map = {"box": PrimitiveType.BOX, "point": PrimitiveType.POINT, "path": PrimitiveType.PATH}
            primitives.append(VisualPrimitive(
                ref=ref,
                primitive_type=type_map[ptype],
                coords=coords,
                token_entropy=0.0,  # entropy not in text format, set default
            ))

        return primitives
