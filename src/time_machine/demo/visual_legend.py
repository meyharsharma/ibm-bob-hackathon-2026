"""Visual legend and onboarding - explains visual encoding to users."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from ..utils.logger import setup_logger
from ..utils.config import Config


class LegendSection(Enum):
    """Sections of the visual legend."""
    BUILDINGS = "buildings"
    COLORS = "colors"
    HEIGHT = "height"
    WEATHERING = "weathering"
    NEIGHBORHOODS = "neighborhoods"
    TIMELINE = "timeline"


@dataclass
class LegendItem:
    """
    Represents a single item in the legend.
    
    Attributes:
        title: Item title
        description: Detailed description
        visual_example: Visual representation (e.g., color code, icon)
        section: Which section this belongs to
    """
    title: str
    description: str
    visual_example: Optional[str] = None
    section: LegendSection = LegendSection.BUILDINGS


@dataclass
class LegendConfig:
    """
    Configuration for visual legend display.
    
    Attributes:
        duration: How long to show legend in seconds (0 = manual dismiss)
        auto_dismiss: Whether to auto-dismiss after duration
        show_on_startup: Whether to show legend on startup
        sections_to_show: Which sections to include
        compact_mode: Whether to use compact display
    """
    duration: float = 15.0
    auto_dismiss: bool = True
    show_on_startup: bool = True
    sections_to_show: Optional[List[LegendSection]] = None
    compact_mode: bool = False
    
    def __post_init__(self):
        """Initialize default sections if not provided."""
        if self.sections_to_show is None:
            self.sections_to_show = list(LegendSection)


class VisualLegend:
    """
    Creates and manages visual encoding legend for onboarding.
    
    This class provides a 15-second onboarding experience that explains
    the visual encoding used in the city visualization. It helps users
    understand what buildings represent, what colors mean, how height
    relates to code complexity, and other visual metaphors.
    
    Features:
    - Comprehensive visual encoding explanation
    - 15-second onboarding experience
    - Customizable sections and duration
    - Compact and full display modes
    - Can be shown as overlay or separate view
    - Supports manual or auto-dismiss
    
    Architecture:
    - Organizes legend into logical sections
    - Provides structured legend data
    - Supports multiple display formats
    - Integrates with demo orchestrator
    
    Visual Encoding Explained:
    - Buildings = Files in the repository
    - Height = Lines of code / complexity
    - Color = File age and activity
    - Weathering = Modification frequency
    - Neighborhoods = Directory structure
    - Timeline = Commit history progression
    
    Example:
        ```python
        legend = VisualLegend()
        
        # Get legend data for display
        legend_data = legend.get_legend_data()
        
        # Show specific section
        buildings_info = legend.get_section(LegendSection.BUILDINGS)
        
        # Get formatted text for overlay
        text = legend.format_as_text()
        ```
    """
    
    def __init__(self, config: Optional[LegendConfig] = None):
        """
        Initialize the visual legend.
        
        Args:
            config: LegendConfig (uses defaults if None)
        """
        self.logger = setup_logger(__name__, level=Config.LOG_LEVEL)
        self.config = config or LegendConfig()
        
        # Build legend items
        self._legend_items = self._build_legend_items()
        
        self.logger.info("Initialized VisualLegend")
    
    def get_legend_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get complete legend data organized by section.
        
        Returns:
            Dictionary mapping section names to lists of legend items
        """
        legend_data = {}
        sections = self.config.sections_to_show or []
        
        for section in sections:
            items = self._get_items_for_section(section)
            legend_data[section.value] = [
                {
                    'title': item.title,
                    'description': item.description,
                    'visual_example': item.visual_example
                }
                for item in items
            ]
        
        return legend_data
    
    def get_section(self, section: LegendSection) -> List[LegendItem]:
        """
        Get legend items for specific section.
        
        Args:
            section: Section to retrieve
            
        Returns:
            List of LegendItem objects for that section
        """
        return self._get_items_for_section(section)
    
    def format_as_text(self, compact: bool = False) -> str:
        """
        Format legend as plain text.
        
        Args:
            compact: Whether to use compact format
            
        Returns:
            Formatted legend text
        """
        lines = ["=== THE TIME MACHINE - VISUAL LEGEND ===", ""]
        sections = self.config.sections_to_show or []
        
        for section in sections:
            items = self._get_items_for_section(section)
            if not items:
                continue
            
            # Section header
            lines.append(f"## {section.value.upper()}")
            lines.append("")
            
            # Items
            for item in items:
                if compact:
                    lines.append(f"• {item.title}: {item.description}")
                else:
                    lines.append(f"### {item.title}")
                    lines.append(f"    {item.description}")
                    if item.visual_example:
                        lines.append(f"    Example: {item.visual_example}")
                    lines.append("")
        
        return "\n".join(lines)
    
    def format_as_html(self) -> str:
        """
        Format legend as HTML.
        
        Returns:
            HTML formatted legend
        """
        html_parts = [
            '<div class="visual-legend">',
            '<h1>The Time Machine - Visual Legend</h1>'
        ]
        sections = self.config.sections_to_show or []
        
        for section in sections:
            items = self._get_items_for_section(section)
            if not items:
                continue
            
            html_parts.append(f'<div class="legend-section">')
            html_parts.append(f'<h2>{section.value.title()}</h2>')
            html_parts.append('<ul>')
            
            for item in items:
                html_parts.append('<li>')
                html_parts.append(f'<strong>{item.title}</strong>: {item.description}')
                if item.visual_example:
                    html_parts.append(f'<span class="example">{item.visual_example}</span>')
                html_parts.append('</li>')
            
            html_parts.append('</ul>')
            html_parts.append('</div>')
        
        html_parts.append('</div>')
        return '\n'.join(html_parts)
    
    def format_as_json(self) -> str:
        """
        Format legend as JSON.
        
        Returns:
            JSON formatted legend
        """
        import json
        return json.dumps(self.get_legend_data(), indent=2)
    
    def get_onboarding_sequence(self) -> List[Dict[str, Any]]:
        """
        Get onboarding sequence for 15-second experience.
        
        Returns:
            List of onboarding steps with timing
        """
        total_duration = self.config.duration
        sections = self.config.sections_to_show
        
        if not sections:
            return []
        
        # Distribute time across sections
        time_per_section = total_duration / len(sections)
        
        sequence = []
        current_time = 0.0
        
        for section in sections:
            items = self._get_items_for_section(section)
            if not items:
                continue
            
            sequence.append({
                'start_time': current_time,
                'duration': time_per_section,
                'section': section.value,
                'title': section.value.title(),
                'items': [
                    {
                        'title': item.title,
                        'description': item.description,
                        'visual_example': item.visual_example
                    }
                    for item in items
                ]
            })
            
            current_time += time_per_section
        
        return sequence
    
    def _build_legend_items(self) -> List[LegendItem]:
        """Build all legend items."""
        items = []
        
        # Buildings section
        items.extend([
            LegendItem(
                title="Buildings = Files",
                description="Each building represents a file in your repository. The building's position corresponds to its directory structure.",
                visual_example="📦 Building",
                section=LegendSection.BUILDINGS
            ),
            LegendItem(
                title="Building Appearance",
                description="Buildings appear when files are created and disappear when deleted. Watch them evolve as your code changes!",
                visual_example="✨ Appear/Disappear",
                section=LegendSection.BUILDINGS
            ),
        ])
        
        # Colors section
        items.extend([
            LegendItem(
                title="Fresh Code (Green/Blue)",
                description="Recently created or heavily modified files appear in vibrant green or blue colors, indicating active development.",
                visual_example="🟢 Green → 🔵 Blue",
                section=LegendSection.COLORS
            ),
            LegendItem(
                title="Mature Code (Yellow/Orange)",
                description="Files that haven't been modified recently transition to warmer colors, showing stability.",
                visual_example="🟡 Yellow → 🟠 Orange",
                section=LegendSection.COLORS
            ),
            LegendItem(
                title="Legacy Code (Red/Gray)",
                description="Old, rarely-touched files appear in red or gray, indicating legacy code that may need attention.",
                visual_example="🔴 Red → ⚫ Gray",
                section=LegendSection.COLORS
            ),
        ])
        
        # Height section
        items.extend([
            LegendItem(
                title="Height = Complexity",
                description="Taller buildings represent larger or more complex files with more lines of code.",
                visual_example="🏢 Tall = More Code",
                section=LegendSection.HEIGHT
            ),
            LegendItem(
                title="Growing Buildings",
                description="Watch buildings grow taller as code is added and shrink when code is removed.",
                visual_example="📈 Growth Animation",
                section=LegendSection.HEIGHT
            ),
        ])
        
        # Weathering section
        items.extend([
            LegendItem(
                title="Weathering = Activity",
                description="Buildings show 'weathering' effects based on modification frequency. More changes = more weathered appearance.",
                visual_example="🏚️ Weathered Surface",
                section=LegendSection.WEATHERING
            ),
            LegendItem(
                title="Hotspots",
                description="Frequently modified files may appear with special effects or highlights, indicating development hotspots.",
                visual_example="🔥 Hotspot Indicator",
                section=LegendSection.WEATHERING
            ),
        ])
        
        # Neighborhoods section
        items.extend([
            LegendItem(
                title="Neighborhoods = Directories",
                description="Buildings are grouped into neighborhoods based on directory structure. Related files cluster together.",
                visual_example="🏘️ Grouped Buildings",
                section=LegendSection.NEIGHBORHOODS
            ),
            LegendItem(
                title="Neighborhood Layout",
                description="Each neighborhood has its own area in the city, making it easy to see your project's organization.",
                visual_example="🗺️ City Layout",
                section=LegendSection.NEIGHBORHOODS
            ),
        ])
        
        # Timeline section
        items.extend([
            LegendItem(
                title="Timeline Playback",
                description="The visualization plays through your repository's history from first commit to latest, showing evolution over time.",
                visual_example="⏯️ Play/Pause",
                section=LegendSection.TIMELINE
            ),
            LegendItem(
                title="Time Controls",
                description="Use playback controls to pause, scrub, or adjust speed. Jump to specific commits or time periods.",
                visual_example="⏩ Speed Control",
                section=LegendSection.TIMELINE
            ),
            LegendItem(
                title="Narration",
                description="Listen to AI-generated narration explaining key moments in your repository's history.",
                visual_example="🎙️ Audio Narration",
                section=LegendSection.TIMELINE
            ),
        ])
        
        return items
    
    def _get_items_for_section(self, section: LegendSection) -> List[LegendItem]:
        """Get legend items for specific section."""
        return [item for item in self._legend_items if item.section == section]
    
    def get_quick_reference(self) -> Dict[str, str]:
        """
        Get quick reference guide (most important points).
        
        Returns:
            Dictionary of key concepts
        """
        return {
            "Buildings": "Each building = one file in your repository",
            "Height": "Taller buildings = more lines of code",
            "Color": "Green (new) → Yellow (stable) → Red (old)",
            "Neighborhoods": "Grouped by directory structure",
            "Timeline": "Watch your code evolve from first to latest commit",
            "Weathering": "More modifications = more weathered appearance"
        }
    
    def get_summary(self) -> str:
        """
        Get brief summary of visual encoding.
        
        Returns:
            Summary text
        """
        return (
            "The Time Machine visualizes your repository as a 3D city. "
            "Each building represents a file, with height showing code size "
            "and color indicating age. Watch your codebase evolve through "
            "time as buildings appear, grow, and change. Neighborhoods group "
            "related files by directory structure."
        )


# Made with Bob