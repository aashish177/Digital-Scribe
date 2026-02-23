import pytest
import json
from pathlib import Path
from utils.exporters import ContentExporter
from datetime import datetime

@pytest.fixture
def exporter():
    return ContentExporter()

@pytest.fixture
def sample_result():
    return {
        "request_id": "test-req-123",
        "started_at": datetime.now().isoformat(),
        "content_request": "Test request",
        "final_content": "# The Test Content\n\nThis is a short test post.\n\n## Subheading\n\nA small detail.",
        "seo_metadata": {
            "meta_title": "Test Title",
            "meta_description": "Test description",
            "slug": "test-content",
            "keywords": ["test", "content"]
        },
        "brief": {
            "title": "Fallback Title",
            "word_count": 500
        },
        "execution_times": {"planner": 1.0, "writer": 2.0},
        "token_usage": {"planner": 100, "writer": 200},
        "errors": []
    }

def test_export_markdown(exporter, sample_result, tmp_path):
    output_path = tmp_path / "content.md"
    result_path = exporter.export_markdown(sample_result, output_path)
    
    assert result_path == output_path
    assert output_path.exists()
    
    content = output_path.read_text(encoding="utf-8")
    
    # Check frontmatter structure
    assert "---" in content
    assert "title: Test Title" in content
    assert "description: Test description" in content
    assert "slug: test-content" in content
    assert "- test" in content
    assert "- content" in content
    
    # Check body content
    assert "# The Test Content" in content
    assert "This is a short test post." in content

def test_export_html(exporter, sample_result, tmp_path):
    output_path = tmp_path / "content.html"
    result_path = exporter.export_html(sample_result, output_path)
    
    assert result_path == output_path
    assert output_path.exists()
    
    content = output_path.read_text(encoding="utf-8")
    
    # Check HTML structure
    assert "<!DOCTYPE html>" in content
    assert "<html lang=\"en\">" in content
    assert "<meta name=\"description\" content=\"Test description\">" in content
    assert "<title>Test Title</title>" in content
    
    # Check markdown-to-html translation
    assert "<h1 id=\"the-test-content\">The Test Content</h1>" in content
    assert "<p>This is a short test post.</p>" in content

def test_export_json(exporter, sample_result, tmp_path):
    output_path = tmp_path / "content.json"
    result_path = exporter.export_json(sample_result, output_path)
    
    assert result_path == output_path
    assert output_path.exists()
    
    data = json.loads(output_path.read_text(encoding="utf-8"))
    
    assert data["request_id"] == "test-req-123"
    assert "final_content" in data
    assert data["seo_metadata"]["meta_title"] == "Test Title"
    assert data["word_count"] == 15 # word count of final content
    
    # test minimal json export
    output_path_min = tmp_path / "content_min.json"
    exporter.export_json(sample_result, output_path_min, include_full_data=False)
    data_min = json.loads(output_path_min.read_text(encoding="utf-8"))
    
    assert "request_id" not in data_min
    assert "content" in data_min
    assert "metadata" in data_min

def test_export_all(exporter, sample_result, tmp_path):
    output_dir = tmp_path / "outputs"
    files = exporter.export_all(sample_result, output_dir, "my_content")
    
    assert len(files) == 3
    assert "markdown" in files
    assert "html" in files
    assert "json" in files
    
    for format_key, file_path in files.items():
        assert file_path.exists()
        assert "my_content" in file_path.name
