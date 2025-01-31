import pytest
from ...app.repositories.tag import tag_repository
from ...app.models.tag import Tag
from ...app.models.document import Document

pytestmark = pytest.mark.asyncio

async def test_get_by_name(db, test_tag):
    """Test getting tag by name."""
    tag = await tag_repository.get_by_name(test_tag.name)
    assert tag is not None
    assert tag.id == test_tag.id

async def test_get_by_name_case_insensitive(db, test_tag):
    """Test getting tag by name is case insensitive."""
    tag = await tag_repository.get_by_name(test_tag.name.upper())
    assert tag is not None
    assert tag.id == test_tag.id

async def test_get_or_create_existing(db, test_tag):
    """Test get_or_create with existing tag."""
    tag = await tag_repository.get_or_create(test_tag.name)
    assert tag.id == test_tag.id

async def test_get_or_create_new(db):
    """Test get_or_create with new tag."""
    name = "new-tag"
    description = "New Tag Description"
    
    tag = await tag_repository.get_or_create(name, description)
    assert tag is not None
    assert tag.name == name.lower()
    assert tag.description == description

async def test_get_or_create_many(db, test_tag):
    """Test get_or_create_many with mix of existing and new tags."""
    names = [test_tag.name, "new-tag-1", "new-tag-2"]
    
    tags = await tag_repository.get_or_create_many(names)
    assert len(tags) == 3
    assert tags[0].id == test_tag.id
    assert tags[1].name == "new-tag-1"
    assert tags[2].name == "new-tag-2"

async def test_search_tags(db):
    """Test searching tags."""
    # Create some test tags
    await tag_repository.get_or_create("python", "Python programming")
    await tag_repository.get_or_create("javascript", "JavaScript programming")
    await tag_repository.get_or_create("typescript", "TypeScript programming")
    
    # Search by name
    tags, total = await tag_repository.search_tags("script")
    assert total == 2
    assert len(tags) == 2
    assert all("script" in tag.name for tag in tags)
    
    # Search by description
    tags, total = await tag_repository.search_tags("programming")
    assert total == 3
    assert len(tags) == 3

async def test_merge_tags(db, test_user):
    """Test merging tags."""
    # Create source and target tags
    source_tag = await tag_repository.get_or_create("source-tag")
    target_tag = await tag_repository.get_or_create("target-tag")
    
    # Create documents using source tag
    doc1 = Document(
        title="Doc 1",
        file_path="/test/1.txt",
        owner=test_user,
        tags=[str(source_tag.id)]
    )
    await doc1.insert()
    
    doc2 = Document(
        title="Doc 2",
        file_path="/test/2.txt",
        owner=test_user,
        tags=[str(source_tag.id)]
    )
    await doc2.insert()
    
    # Merge tags
    await tag_repository.merge_tags(source_tag, target_tag)
    
    # Verify source tag is deleted
    assert await tag_repository.get(str(source_tag.id)) is None
    
    # Verify documents now use target tag
    doc1 = await Document.get(doc1.id)
    doc2 = await Document.get(doc2.id)
    assert str(target_tag.id) in doc1.tags
    assert str(target_tag.id) in doc2.tags
    assert str(source_tag.id) not in doc1.tags
    assert str(source_tag.id) not in doc2.tags

async def test_get_tag_usage_stats(db, test_user):
    """Test getting tag usage statistics."""
    # Create tags
    tag1 = await tag_repository.get_or_create("tag1")
    tag2 = await tag_repository.get_or_create("tag2")
    tag3 = await tag_repository.get_or_create("tag3")
    
    # Create documents with tags
    doc1 = Document(
        title="Doc 1",
        file_path="/test/1.txt",
        owner=test_user,
        tags=[str(tag1.id)]
    )
    await doc1.insert()
    
    doc2 = Document(
        title="Doc 2",
        file_path="/test/2.txt",
        owner=test_user,
        tags=[str(tag1.id), str(tag2.id)]
    )
    await doc2.insert()
    
    # Get stats
    stats = await tag_repository.get_tag_usage_stats()
    
    # Verify stats
    tag1_stats = next(s for s in stats if s["name"] == "tag1")
    tag2_stats = next(s for s in stats if s["name"] == "tag2")
    tag3_stats = next(s for s in stats if s["name"] == "tag3")
    
    assert tag1_stats["document_count"] == 2
    assert tag2_stats["document_count"] == 1
    assert tag3_stats["document_count"] == 0

async def test_get_unused_tags(db, test_user):
    """Test getting unused tags."""
    # Create tags
    used_tag = await tag_repository.get_or_create("used-tag")
    unused_tag = await tag_repository.get_or_create("unused-tag")
    
    # Create document with used tag
    doc = Document(
        title="Doc",
        file_path="/test/doc.txt",
        owner=test_user,
        tags=[str(used_tag.id)]
    )
    await doc.insert()
    
    # Get unused tags
    unused_tags = await tag_repository.get_unused_tags()
    assert len(unused_tags) == 1
    assert unused_tags[0].id == unused_tag.id

async def test_cleanup_unused_tags(db, test_user):
    """Test cleaning up unused tags."""
    # Create tags
    used_tag = await tag_repository.get_or_create("used-tag")
    unused_tag1 = await tag_repository.get_or_create("unused-tag-1")
    unused_tag2 = await tag_repository.get_or_create("unused-tag-2")
    
    # Create document with used tag
    doc = Document(
        title="Doc",
        file_path="/test/doc.txt",
        owner=test_user,
        tags=[str(used_tag.id)]
    )
    await doc.insert()
    
    # Clean up unused tags
    deleted_count = await tag_repository.cleanup_unused_tags()
    assert deleted_count == 2
    
    # Verify only used tag remains
    remaining_tags = await Tag.find_all().to_list()
    assert len(remaining_tags) == 1
    assert remaining_tags[0].id == used_tag.id 