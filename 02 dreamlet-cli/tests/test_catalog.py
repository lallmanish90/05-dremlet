from dreamlet_cli.catalog import load_catalog


def test_catalog_contains_full_page_surface():
    catalog = load_catalog()

    assert len(catalog) == 37
    assert "01" in catalog
    assert "06" in catalog
    assert "06-4k-image" in catalog
    assert "06-4k-image-pptx-zip" in catalog
    assert "08-ollama" in catalog
    assert "08-translator-lm-studio" in catalog
    assert "11-workflow-manager" in catalog
    assert "99-01-rename-backup" in catalog


def test_catalog_marks_broken_source_pages_for_patch_work():
    catalog = load_catalog()

    assert catalog["52"].source_compiles is False
    assert catalog["53"].source_compiles is False
    assert catalog["54"].source_compiles is False
    assert catalog["55"].source_compiles is False
