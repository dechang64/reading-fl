"""
twc_core.gradcam — Grad-CAM Explainability
==========================================
Unified Grad-CAM extracted from organoid-fl, defect-fl, and embodied-fl.

Usage:
    from twc_core.gradcam import GradCAM
    cam = GradCAM(model, target_layer=model.layer4)
    heatmap = cam.generate(image_tensor, target_class=1)
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from typing import Optional, Tuple


class GradCAM:
    """Gradient-weighted Class Activation Mapping.

    Works with any CNN (ResNet, VGG, EfficientNet, etc.).
    Auto-detects target layer if not specified.

    Usage:
        cam = GradCAM(model)
        heatmap = cam.generate(image_tensor, target_class=0)
        overlay = cam.overlay(image_path, heatmap)
    """

    def __init__(self, model: nn.Module, target_layer: Optional[nn.Module] = None):
        self.model = model
        self.model.eval()
        self.gradients = None
        self.activations = None

        if target_layer is None:
            target_layer = self._auto_detect_target_layer()

        self.target_layer = target_layer
        self._register_hooks()

    def _auto_detect_target_layer(self) -> nn.Module:
        """Auto-detect the last conv layer."""
        for module in reversed(list(self.model.modules())):
            if isinstance(module, nn.Conv2d):
                return module
        raise ValueError("No Conv2d layer found in model")

    def _register_hooks(self):
        """Register forward and backward hooks."""
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate(self, image_tensor: torch.Tensor, target_class: Optional[int] = None,
                 size: Tuple[int, int] = (224, 224)) -> np.ndarray:
        """Generate Grad-CAM heatmap.

        Args:
            image_tensor: Input image tensor, shape (1, 3, H, W).
            target_class: Target class index. If None, uses predicted class.
            size: Output heatmap size.

        Returns:
            Heatmap as numpy array, shape (H, W), values in [0, 1].
        """
        output = self.model(image_tensor)

        if target_class is None:
            target_class = output.argmax(dim=1).item()

        self.model.zero_grad()
        output[0, target_class].backward()

        # Weighted combination of feature maps
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)

        # Normalize
        cam = cam.squeeze().cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()

        # Resize to target size
        from torchvision.transforms.functional import resize
        cam_tensor = torch.tensor(cam).unsqueeze(0).unsqueeze(0)
        cam_resized = resize(cam_tensor, size, antialias=True)
        return cam_resized.squeeze().numpy()

    def overlay(self, image, heatmap: np.ndarray, alpha: float = 0.4) -> np.ndarray:
        """Overlay heatmap on original image.

        Args:
            image: Path to image (str) or numpy array (H, W, 3).
            heatmap: Grad-CAM heatmap from generate().
            alpha: Overlay transparency.

        Returns:
            Blended image as numpy array (H, W, 3), uint8.
        """
        import cv2
        if isinstance(image, str):
            img = cv2.imread(image)
        elif isinstance(image, np.ndarray):
            img = image.copy()
        else:
            raise TypeError(f"image must be str or np.ndarray, got {type(image)}")
        img = cv2.resize(img, (heatmap.shape[1], heatmap.shape[0]))

        heatmap_colored = cv2.applyColorMap((heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)
        blended = cv2.addWeighted(img, 1 - alpha, heatmap_colored, alpha, 0)
        return blended
