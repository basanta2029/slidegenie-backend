"""Tests for slide layout system."""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from app.services.slides.interfaces import ILayoutEngine, SlideContent
from app.services.slides.config import LayoutStyle


class MockLayoutEngine(ILayoutEngine):
    """Mock implementation of layout engine."""
    
    def __init__(self):
        self.available_layouts = {
            "minimal": ["title", "content", "two_column", "image_left"],
            "modern": ["title", "content", "grid", "hero", "comparison"],
            "academic": ["title", "content", "citation", "data_table", "figure"],
            "business": ["title", "content", "chart", "timeline", "team"],
            "creative": ["title", "full_image", "collage", "quote", "gallery"]
        }
        self.apply_layout_calls = 0
        self.optimize_layout_calls = 0
    
    def get_available_layouts(self, style: str) -> List[str]:
        if style and style in self.available_layouts:
            return self.available_layouts[style]
        # Return all layouts if no style specified
        all_layouts = set()
        for layouts in self.available_layouts.values():
            all_layouts.update(layouts)
        return sorted(list(all_layouts))
    
    def apply_layout(
        self,
        slide: SlideContent,
        layout_name: str,
        style_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        self.apply_layout_calls += 1
        
        # Basic layout application logic
        layout_data = {
            "layout": layout_name,
            "elements": []
        }
        
        # Add title element
        if slide.title:
            layout_data["elements"].append({
                "type": "title",
                "content": slide.title,
                "position": {"x": 0, "y": 0, "width": "100%", "height": "20%"}
            })
        
        # Add content based on layout
        if layout_name == "two_column" and slide.bullet_points:
            # Split bullet points into two columns
            mid = len(slide.bullet_points) // 2
            layout_data["elements"].extend([
                {
                    "type": "bullet_list",
                    "items": slide.bullet_points[:mid],
                    "position": {"x": 0, "y": "25%", "width": "45%", "height": "70%"}
                },
                {
                    "type": "bullet_list",
                    "items": slide.bullet_points[mid:],
                    "position": {"x": "50%", "y": "25%", "width": "45%", "height": "70%"}
                }
            ])
        elif slide.content:
            layout_data["elements"].append({
                "type": "text",
                "content": slide.content,
                "position": {"x": 0, "y": "25%", "width": "100%", "height": "70%"}
            })
        
        # Apply style options
        if style_options:
            layout_data["style"] = style_options
        
        return layout_data
    
    def optimize_layout(
        self,
        slide: SlideContent,
        constraints: Dict[str, Any] = None
    ) -> SlideContent:
        self.optimize_layout_calls += 1
        
        # Determine best layout based on content
        if slide.visual_elements and len(slide.visual_elements) > 0:
            if len(slide.visual_elements) > 3:
                slide.layout_type = "gallery"
            else:
                slide.layout_type = "image_left"
        elif slide.bullet_points and len(slide.bullet_points) > 4:
            slide.layout_type = "two_column"
        elif not slide.content and slide.title:
            slide.layout_type = "title"
        else:
            slide.layout_type = "content"
        
        # Apply constraints
        if constraints:
            if constraints.get("style") == "minimal":
                # Simplify layout for minimal style
                if slide.layout_type in ["gallery", "image_left"]:
                    slide.layout_type = "content"
        
        return slide


class TestLayoutEngine:
    """Test suite for layout engine."""
    
    @pytest.fixture
    def engine(self):
        """Create layout engine instance."""
        return MockLayoutEngine()
    
    @pytest.fixture
    def sample_slide(self):
        """Create sample slide."""
        return SlideContent(
            title="Sample Slide",
            content="This is the main content",
            bullet_points=["Point 1", "Point 2", "Point 3"],
            layout_type="content"
        )
    
    def test_get_available_layouts_by_style(self, engine):
        """Test getting layouts for specific styles."""
        minimal_layouts = engine.get_available_layouts("minimal")
        assert "title" in minimal_layouts
        assert "content" in minimal_layouts
        assert "two_column" in minimal_layouts
        assert len(minimal_layouts) == 4
        
        modern_layouts = engine.get_available_layouts("modern")
        assert "hero" in modern_layouts
        assert "grid" in modern_layouts
        assert len(modern_layouts) == 5
        
        academic_layouts = engine.get_available_layouts("academic")
        assert "citation" in academic_layouts
        assert "data_table" in academic_layouts
    
    def test_get_all_available_layouts(self, engine):
        """Test getting all layouts when no style specified."""
        all_layouts = engine.get_available_layouts("")
        
        # Should contain layouts from all styles
        assert "title" in all_layouts
        assert "hero" in all_layouts
        assert "citation" in all_layouts
        assert "chart" in all_layouts
        assert "collage" in all_layouts
        
        # Should be unique
        assert len(all_layouts) == len(set(all_layouts))
    
    def test_apply_basic_layout(self, engine, sample_slide):
        """Test applying a basic layout."""
        result = engine.apply_layout(sample_slide, "content")
        
        assert result["layout"] == "content"
        assert len(result["elements"]) == 2  # Title and content
        
        # Check title element
        title_elem = next(e for e in result["elements"] if e["type"] == "title")
        assert title_elem["content"] == sample_slide.title
        
        # Check content element
        content_elem = next(e for e in result["elements"] if e["type"] == "text")
        assert content_elem["content"] == sample_slide.content
        
        assert engine.apply_layout_calls == 1
    
    def test_apply_two_column_layout(self, engine):
        """Test applying two-column layout."""
        slide = SlideContent(
            title="Two Column Test",
            bullet_points=["Point 1", "Point 2", "Point 3", "Point 4", "Point 5", "Point 6"]
        )
        
        result = engine.apply_layout(slide, "two_column")
        
        assert result["layout"] == "two_column"
        
        # Should have title and two bullet lists
        bullet_lists = [e for e in result["elements"] if e["type"] == "bullet_list"]
        assert len(bullet_lists) == 2
        
        # First column should have first half of points
        assert len(bullet_lists[0]["items"]) == 3
        assert bullet_lists[0]["items"][0] == "Point 1"
        
        # Second column should have second half
        assert len(bullet_lists[1]["items"]) == 3
        assert bullet_lists[1]["items"][0] == "Point 4"
    
    def test_apply_layout_with_style_options(self, engine, sample_slide):
        """Test applying layout with style options."""
        style_options = {
            "background_color": "#ffffff",
            "font_size": 16,
            "padding": 20
        }
        
        result = engine.apply_layout(sample_slide, "content", style_options)
        
        assert "style" in result
        assert result["style"]["background_color"] == "#ffffff"
        assert result["style"]["font_size"] == 16
        assert result["style"]["padding"] == 20
    
    def test_optimize_layout_for_images(self, engine):
        """Test layout optimization for slides with images."""
        slide = SlideContent(
            title="Image Slide",
            content="Some content",
            visual_elements=[
                {"type": "image", "src": "img1.jpg"},
                {"type": "image", "src": "img2.jpg"}
            ]
        )
        
        optimized = engine.optimize_layout(slide)
        
        assert optimized.layout_type == "image_left"
        assert engine.optimize_layout_calls == 1
    
    def test_optimize_layout_for_many_images(self, engine):
        """Test layout optimization for slides with many images."""
        slide = SlideContent(
            title="Gallery",
            visual_elements=[
                {"type": "image", "src": f"img{i}.jpg"}
                for i in range(5)
            ]
        )
        
        optimized = engine.optimize_layout(slide)
        
        assert optimized.layout_type == "gallery"
    
    def test_optimize_layout_for_many_bullets(self, engine):
        """Test layout optimization for slides with many bullet points."""
        slide = SlideContent(
            title="Many Points",
            bullet_points=[f"Point {i}" for i in range(8)]
        )
        
        optimized = engine.optimize_layout(slide)
        
        assert optimized.layout_type == "two_column"
    
    def test_optimize_layout_with_constraints(self, engine):
        """Test layout optimization with constraints."""
        slide = SlideContent(
            title="Constrained",
            visual_elements=[{"type": "image", "src": "img.jpg"}]
        )
        
        constraints = {"style": "minimal"}
        optimized = engine.optimize_layout(slide, constraints)
        
        # Should simplify to content layout for minimal style
        assert optimized.layout_type == "content"
    
    def test_optimize_title_only_slide(self, engine):
        """Test optimization for title-only slides."""
        slide = SlideContent(title="Title Only Slide")
        
        optimized = engine.optimize_layout(slide)
        
        assert optimized.layout_type == "title"


class TestLayoutStyles:
    """Test different layout styles."""
    
    @pytest.fixture
    def engine(self):
        return MockLayoutEngine()
    
    @pytest.mark.parametrize("style,expected_layouts", [
        ("minimal", ["title", "content", "two_column", "image_left"]),
        ("modern", ["title", "content", "grid", "hero", "comparison"]),
        ("academic", ["title", "content", "citation", "data_table", "figure"]),
        ("business", ["title", "content", "chart", "timeline", "team"]),
        ("creative", ["title", "full_image", "collage", "quote", "gallery"])
    ])
    def test_style_specific_layouts(self, engine, style, expected_layouts):
        """Test that each style has its specific layouts."""
        layouts = engine.get_available_layouts(style)
        assert set(layouts) == set(expected_layouts)


class TestLayoutEdgeCases:
    """Test edge cases for layout system."""
    
    @pytest.fixture
    def engine(self):
        return MockLayoutEngine()
    
    def test_empty_slide_layout(self, engine):
        """Test layout for empty slide."""
        empty_slide = SlideContent()
        
        result = engine.apply_layout(empty_slide, "content")
        
        assert result["layout"] == "content"
        assert len(result["elements"]) == 0  # No elements for empty slide
    
    def test_slide_with_only_title(self, engine):
        """Test layout for slide with only title."""
        title_slide = SlideContent(title="Only Title")
        
        result = engine.apply_layout(title_slide, "title")
        
        assert len(result["elements"]) == 1
        assert result["elements"][0]["type"] == "title"
    
    def test_very_long_content(self, engine):
        """Test layout with very long content."""
        long_slide = SlideContent(
            title="Long Content",
            content="x" * 1000  # Very long content
        )
        
        result = engine.apply_layout(long_slide, "content")
        
        # Should still create layout
        assert len(result["elements"]) == 2
        content_elem = next(e for e in result["elements"] if e["type"] == "text")
        assert len(content_elem["content"]) == 1000
    
    def test_odd_number_bullet_points_two_column(self, engine):
        """Test two-column layout with odd number of bullets."""
        slide = SlideContent(
            title="Odd Bullets",
            bullet_points=["1", "2", "3", "4", "5"]  # 5 points
        )
        
        result = engine.apply_layout(slide, "two_column")
        
        bullet_lists = [e for e in result["elements"] if e["type"] == "bullet_list"]
        # First column gets 2, second gets 3
        assert len(bullet_lists[0]["items"]) == 2
        assert len(bullet_lists[1]["items"]) == 3


class TestLayoutIntegration:
    """Integration tests for layout system."""
    
    def test_layout_style_enum(self):
        """Test LayoutStyle enum values."""
        assert LayoutStyle.MINIMAL.value == "minimal"
        assert LayoutStyle.MODERN.value == "modern"
        assert LayoutStyle.ACADEMIC.value == "academic"
        assert LayoutStyle.BUSINESS.value == "business"
        assert LayoutStyle.CREATIVE.value == "creative"
    
    def test_complete_layout_workflow(self):
        """Test complete layout workflow."""
        engine = MockLayoutEngine()
        
        # Create presentation with various slide types
        slides = [
            SlideContent(title="Title Slide"),
            SlideContent(
                title="Content Slide",
                content="Main content here"
            ),
            SlideContent(
                title="Bullet Slide",
                bullet_points=["A", "B", "C", "D", "E", "F"]
            ),
            SlideContent(
                title="Image Slide",
                content="With images",
                visual_elements=[{"type": "image", "src": "img.jpg"}]
            )
        ]
        
        # Optimize layouts
        optimized_slides = []
        for slide in slides:
            optimized = engine.optimize_layout(slide, {"style": "modern"})
            optimized_slides.append(optimized)
        
        # Verify optimizations
        assert optimized_slides[0].layout_type == "title"
        assert optimized_slides[1].layout_type == "content"
        assert optimized_slides[2].layout_type == "two_column"
        assert optimized_slides[3].layout_type == "image_left"
        
        # Apply layouts
        layouts = []
        for slide in optimized_slides:
            layout = engine.apply_layout(slide, slide.layout_type)
            layouts.append(layout)
        
        # Verify applications
        assert all(layout["layout"] == slide.layout_type 
                  for layout, slide in zip(layouts, optimized_slides))
        
        assert engine.optimize_layout_calls == 4
        assert engine.apply_layout_calls == 4