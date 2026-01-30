from doc_weaver.document import Document, SubSection, Content

class TestContent:
    
    def test_content_creation(self):
        content = Content("Test content")
        assert content.text == "Test content"
        assert content.id is not None
        assert len(content.id) > 0
    
    def test_content_with_custom_id(self):
        custom_id = "custom-123"
        content = Content("Test", id=custom_id)
        assert content.id == custom_id
    
    def test_content_str_with_text(self):
        content = Content("Hello world")
        assert str(content) == "Hello world"
    
    def test_content_str_empty(self):
        content = Content("")
        assert str(content) == ""
    
    def test_unique_ids(self):
        content1 = Content("First")
        content2 = Content("Second")
        assert content1.id != content2.id


class TestSubSection:
    
    def test_subsection_creation(self):
        subsection = SubSection("My Subsection")
        assert subsection.title == "My Subsection"
        assert subsection.items == []
        assert subsection.id is not None
    
    def test_subsection_with_items(self):
        items = [Content("Item 1"), Content("Item 2")]
        subsection = SubSection("My Subsection", items=items)
        assert subsection.title == "My Subsection"
        assert len(subsection.items) == 2
    
    def test_subsection_with_custom_id(self):
        custom_id = "subsec-456"
        subsection = SubSection("Title", id=custom_id)
        assert subsection.id == custom_id
    
    def test_add_content_append(self):
        subsection = SubSection("Skills")
        content = Content("Python")
        subsection.add_content(content)
        assert len(subsection.items) == 1
        assert subsection.items[0].text == "Python"
    
    def test_add_content_at_index(self):
        subsection = SubSection("Skills")
        content1 = Content("Python")
        content2 = Content("JavaScript")
        content3 = Content("Go")
        
        subsection.add_content(content1)
        subsection.add_content(content2)
        subsection.add_content(content3, index=1)
        
        assert len(subsection.items) == 3
        assert subsection.items[0].text == "Python"
        assert subsection.items[1].text == "Go"
        assert subsection.items[2].text == "JavaScript"
    
    def test_subsection_str(self):
        subsection = SubSection("Skills")
        subsection.add_content(Content("Python"))
        subsection.add_content(Content("JavaScript"))
        
        expected = "### Skills\n- Python\n- JavaScript\n"
        assert str(subsection) == expected
    
    def test_subsection_str_empty(self):
        subsection = SubSection("Empty Section")
        expected = "### Empty Section\n"
        assert str(subsection) == expected
    
    def test_items_isolation(self):
        subsection1 = SubSection("Section 1")
        subsection2 = SubSection("Section 2")
        
        subsection1.add_content(Content("Content 1"))
        
        assert len(subsection1.items) == 1
        assert len(subsection2.items) == 0


class TestDocument:
    
    def test_document_creation(self):
        doc = Document("My Title", "My Tagline")
        assert doc.header == "My Title"
        assert doc.tagline == "My Tagline"
        assert doc.sections == {}
        assert doc.id is not None
    
    def test_document_with_custom_id(self):
        custom_id = "doc-789"
        doc = Document("Title", "Tagline", id=custom_id)
        assert doc.id == custom_id
    
    def test_create_section(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Work Experience")
        
        assert "Work Experience" in doc.sections
        assert doc.sections["Work Experience"] == []
    
    def test_create_multiple_sections(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Education")
        doc.create_section("Skills")
        doc.create_section("Projects")
        
        assert len(doc.sections) == 3
        assert "Education" in doc.sections
        assert "Skills" in doc.sections
        assert "Projects" in doc.sections
    
    def test_create_subsection_single(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Skills")
        doc.create_subsection("Skills", "Technical Skills")
        
        assert len(doc.sections["Skills"]) == 1
        assert doc.sections["Skills"][0].title == "Technical Skills"
    
    def test_create_subsection_multiple(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Skills")
        doc.create_subsection("Skills", ["Technical", "Soft Skills", "Languages"])
        
        assert len(doc.sections["Skills"]) == 3
        assert doc.sections["Skills"][0].title == "Technical"
        assert doc.sections["Skills"][1].title == "Soft Skills"
        assert doc.sections["Skills"][2].title == "Languages"
    
    def test_create_subsection_creates_section_if_missing(self):
        doc = Document("Title", "Tagline")
        doc.create_subsection("New Section", "Subsection")
        
        assert "New Section" in doc.sections
        assert len(doc.sections["New Section"]) == 1
    
    def test_create_content(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Projects")
        doc.create_subsection("Projects", "Project A")
        
        subsection_id = doc.sections["Projects"][0].id
        doc.create_content("Projects", subsection_id, "Built a web app")
        
        assert len(doc.sections["Projects"][0].items) == 1
        assert doc.sections["Projects"][0].items[0].text == "Built a web app"
    
    def test_create_content_wrong_subsection_id(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Projects")
        doc.create_subsection("Projects", "Project A")
        
        # Use a non-existent ID
        doc.create_content("Projects", "wrong-id", "Some content")
        
        # Content should not be added
        assert len(doc.sections["Projects"][0].items) == 0
    
    def test_create_content_creates_section_if_missing(self):
        doc = Document("Title", "Tagline")
        doc.create_content("New Section", "some-id", "Content")
        
        assert "New Section" in doc.sections
        assert doc.sections["New Section"] == []
    
    def test_preview_basic(self):
        doc = Document("John Doe", "Software Engineer")
        preview = doc.preview()
        
        assert "# John Doe" in preview
        assert "> Software Engineer" in preview
    
    def test_preview_with_sections(self):
        doc = Document("Jane Smith", "Data Scientist")
        doc.create_section("Education")
        doc.create_subsection("Education", "University")
        
        subsection_id = doc.sections["Education"][0].id
        doc.create_content("Education", subsection_id, "BS in Computer Science")
        
        preview = doc.preview()
        
        assert "# Jane Smith" in preview
        assert "> Data Scientist" in preview
        assert "## Education" in preview
        assert "### University" in preview
        assert "- BS in Computer Science" in preview
    
    def test_preview_multiple_sections(self):
        doc = Document("Title", "Tagline")
        doc.create_section("Section 1")
        doc.create_section("Section 2")
        doc.create_subsection("Section 1", "Sub 1")
        doc.create_subsection("Section 2", "Sub 2")
        
        preview = doc.preview()
        
        assert "## Section 1" in preview
        assert "## Section 2" in preview
        assert "### Sub 1" in preview
        assert "### Sub 2" in preview
    
    def test_sections_isolation(self):
        doc1 = Document("Doc 1", "Tagline 1")
        doc2 = Document("Doc 2", "Tagline 2")
        
        doc1.create_section("Section A")
        
        assert "Section A" in doc1.sections
        assert "Section A" not in doc2.sections
        assert len(doc2.sections) == 0
    
    def test_unique_document_ids(self):
        doc1 = Document("Title 1", "Tagline 1")
        doc2 = Document("Title 2", "Tagline 2")
        
        assert doc1.id != doc2.id
    
    def test_complex_document_structure(self):
        doc = Document("Resume", "Professional Summary")
        
        # Add work experience
        doc.create_section("Work Experience")
        doc.create_subsection("Work Experience", ["Company A", "Company B"])
        
        company_a_id = doc.sections["Work Experience"][0].id
        company_b_id = doc.sections["Work Experience"][1].id
        
        doc.create_content("Work Experience", company_a_id, "Software Engineer")
        doc.create_content("Work Experience", company_a_id, "2020-2022")
        doc.create_content("Work Experience", company_b_id, "Senior Developer")
        
        # Add skills
        doc.create_section("Skills")
        doc.create_subsection("Skills", "Technical")
        
        tech_id = doc.sections["Skills"][0].id
        doc.create_content("Skills", tech_id, "Python")
        doc.create_content("Skills", tech_id, "JavaScript")
        
        # Verify structure
        assert len(doc.sections) == 2
        assert len(doc.sections["Work Experience"]) == 2
        assert len(doc.sections["Work Experience"][0].items) == 2
        assert len(doc.sections["Work Experience"][1].items) == 1
        assert len(doc.sections["Skills"][0].items) == 2
        
        # Verify preview
        preview = doc.preview()
        assert "# Resume" in preview
        assert "## Work Experience" in preview
        assert "## Skills" in preview
        assert "- Python" in preview
    