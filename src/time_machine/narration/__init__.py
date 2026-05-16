"""Narration module - AI-generated narration for repository visualization."""

from .bob_client import (
    BobClient,
    NarrationRequest,
    NarrationResponse,
    NarrationType
)
from .epoch_generator import (
    EpochGenerator,
    Epoch,
    EpochNarration
)
from .narration_sync import (
    NarrationSync,
    NarrationSegment,
    NarrationState
)
from .building_explainer import (
    BuildingExplainer,
    BuildingExplanation
)
from .narration_storage import NarrationStorage

__all__ = [
    # Bob Client
    'BobClient',
    'NarrationRequest',
    'NarrationResponse',
    'NarrationType',
    # Epoch Generator
    'EpochGenerator',
    'Epoch',
    'EpochNarration',
    # Narration Sync
    'NarrationSync',
    'NarrationSegment',
    'NarrationState',
    # Building Explainer
    'BuildingExplainer',
    'BuildingExplanation',
    # Storage
    'NarrationStorage',
]

# Made with Bob
