"""
twc_core.features — Feature Extraction (DINOv2 / ResNet18)
===========================================================
Unified feature extractor extracted from organoid-fl (DINOv2Extractor).

Usage:
    from twc_core.features import DINOv2Extractor, get_extractor
    extractor = get_extractor("dinov2", model_name="facebook/dinov2-base")
    features = extractor.extract("image.jpg")  # np.ndarray, shape (768,)
"""

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from typing import Optional
from torchvision import transforms


class DINOv2Extractor(nn.Module):
    """DINOv2-based feature extractor using CLS token.

    Models:
        facebook/dinov2-vits14   → 384-dim, 22M params (fastest)
        facebook/dinov2-base     → 768-dim, 86M params (recommended)
        facebook/dinov2-large    → 1024-dim, 300M params (best quality)
    """

    MODEL_DIMS = {
        "vits14": 384,
        "base": 768,
        "large": 1024,
        "giant": 1536,
    }

    def __init__(self, model_name: str = "facebook/dinov2-base", device: Optional[str] = None):
        super().__init__()
        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Determine dimension from model name
        self.dim = 768  # default
        for key, dim in self.MODEL_DIMS.items():
            if key in model_name:
                self.dim = dim
                break

        # Lazy load model
        self._model = None
        self._transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    def _ensure_model(self):
        """Load model on first use."""
        if self._model is None:
            self._model = torch.hub.load("facebookresearch/dinov2", self.model_name)
            self._model = self._model.to(self.device)
            self._model.eval()

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Extract features from image tensor.

        Args:
            x: Image tensor, shape (B, 3, H, W).

        Returns:
            Feature tensor, shape (B, dim).
        """
        self._ensure_model()
        x = x.to(self.device)
        features = self._model(x)
        if isinstance(features, dict):
            return features["cls_token"]
        return features

    @torch.no_grad()
    def extract(self, image_path: str) -> np.ndarray:
        """Extract feature vector from a single image file.

        Args:
            image_path: Path to image file.

        Returns:
            Feature vector, shape (dim,).
        """
        img = Image.open(image_path).convert("RGB")
        x = self._transform(img).unsqueeze(0)
        feat = self.forward(x)
        return feat.squeeze(0).cpu().numpy()

    @torch.no_grad()
    def extract_batch(self, image_paths: list[str]) -> np.ndarray:
        """Extract features from multiple images.

        Args:
            image_paths: List of image file paths.

        Returns:
            Feature matrix, shape (N, dim).
        """
        tensors = []
        for path in image_paths:
            img = Image.open(path).convert("RGB")
            tensors.append(self._transform(img))
        x = torch.stack(tensors)
        feat = self.forward(x)
        return feat.cpu().numpy()

    def get_trainable_params(self) -> dict:
        """Return model parameters (for FL weight exchange)."""
        self._ensure_model()
        return {k: v.cpu().numpy() for k, v in self._model.named_parameters()}

    def load_params(self, state_dict: dict):
        """Load model parameters (for FL weight exchange)."""
        self._ensure_model()
        state = {k: torch.tensor(v) for k, v in state_dict.items()}
        try:
            self._model.load_state_dict(state, strict=False)
        except RuntimeError as e:
            raise ValueError(
                f"Weight shape mismatch: {e}. "
                "Ensure the state dict comes from a compatible model."
            ) from e


class ResNet18Extractor(nn.Module):
    """ResNet-18 feature extractor (lightweight fallback)."""

    def __init__(self, device: Optional[str] = None):
        super().__init__()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.dim = 512
        self._model = None
        self._transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    def _ensure_model(self):
        if self._model is None:
            import torchvision.models as models
            resnet = models.resnet18(pretrained=False)
            resnet.fc = nn.Identity()
            self._model = resnet.to(self.device)
            self._model.eval()

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        self._ensure_model()
        return self._model(x.to(self.device))

    @torch.no_grad()
    def extract(self, image_path: str) -> np.ndarray:
        img = Image.open(image_path).convert("RGB")
        x = self._transform(img).unsqueeze(0)
        feat = self.forward(x)
        return feat.squeeze(0).cpu().numpy()


def get_extractor(model_type: str = "dinov2", **kwargs):
    """Factory function for feature extractors.

    Args:
        model_type: "dinov2" or "resnet18".
        **kwargs: Passed to extractor constructor.

    Returns:
        Feature extractor instance.
    """
    if model_type == "dinov2":
        return DINOv2Extractor(**kwargs)
    elif model_type == "resnet18":
        return ResNet18Extractor(**kwargs)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
