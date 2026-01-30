class TestLoadMarkdown:

    class TestPositiveCases:

        def test_normal_markdown(self):
            from doc_weaver.parser import load_markdown
            normal_md = """# John Doe - Software Engineer
> Experienced Software Engineer with a passion for developing innovative programs that expedite the efficiency and effectiveness of organizational success.
## History
### Work
- Developed multiple web applications using Python and JavaScript.
- Led a team of 5 engineers to deliver projects on time.
### Education
- Bachelor of Science in Computer Science from XYZ University.
## Skills
### Key Skills
- <TODO>
- Team Leadership
### Technical Skills
- Python, JavaScript, Go
- Docker, Kubernetes
### Soft Skills
- Communication
- Time Management
### Languages
- English (Fluent)
- Spanish (Intermediate)"""
            doc = load_markdown(normal_md, check_todo=True)
            assert doc.header == "John Doe - Software Engineer"
            assert "Experienced Software Engineer" in doc.tagline
            assert "History" in doc.sections
            assert "Skills" in doc.sections
            assert len(doc.sections["Skills"]) == 4

        def test_short_markdown(self):
            from doc_weaver.parser import load_markdown
            short_md = """# Title\n> <TODO>"""
            doc2 = load_markdown(short_md, check_todo=True)
            assert doc2.tagline == "<TODO>"
            assert doc2.header == "Title"

        def test_long_markdown(self):
            from doc_weaver.parser import load_markdown
            long_md = "# Title\n> Tagline\n"
            for i in range(150):
                long_md += f"## Section {i}\n"
                for j in range(5):
                    long_md += f"### Subsection {j}\n"
                    if i == 0 and j == 0:
                        long_md += "- <TODO>\n"
                    else:
                        for k in range(3):
                            long_md += f"- Content item {k}\n"
            doc = load_markdown(long_md, check_todo=True)
            assert doc.header == "Title"
            assert len(doc.sections) == 150

        def test_content_todo(self):
            from doc_weaver.parser import load_markdown
            todo_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
## Projects
### Project A
- <TODO>"""
            doc = load_markdown(todo_md, check_todo=True)
            assert doc.header == "Jane Smith - Data Scientist"
            assert "<TODO>" in doc.preview()

        def test_section_todo(self):
            from doc_weaver.parser import load_markdown
            todo_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
## <TODO>
### Project A
- Completed data analysis for client X."""
            doc = load_markdown(todo_md, check_todo=True)
            assert "<TODO>" in doc.sections
            assert "<TODO>" in doc.preview()

        def test_subsection_todo(self):
            from doc_weaver.parser import load_markdown
            todo_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
## Projects
### <TODO>
- Completed data analysis for client X."""
            doc = load_markdown(todo_md, check_todo=True)
            assert doc.sections["Projects"][0].title == "<TODO>"
            assert "<TODO>" in doc.preview()

        def test_title_todo(self):
            from doc_weaver.parser import load_markdown
            todo_md = """# <TODO>
> Passionate about data and analytics.
## Projects
### Project A
- Completed data analysis for client X."""
            doc = load_markdown(todo_md, check_todo=True)
            assert doc.header == "<TODO>"
            assert "<TODO>" in doc.preview()

        def test_tagline_todo(self):
            from doc_weaver.parser import load_markdown
            todo_md = """# Jane Smith - Data Scientist
> <TODO>
## Projects
### Project A
- Completed data analysis for client X."""
            doc = load_markdown(todo_md, check_todo=True)
            assert doc.tagline == "<TODO>"
            assert "<TODO>" in doc.preview()

    class TestNegativeCases:

        def test_multiple_todos(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
## Projects
### Project A
- <TODO>
- Another item
### Project B
- <TODO>"""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for multiple TODOs"
            except ValidationError as e:
                assert "exactly one <TODO>" in str(e)

        def test_no_todo(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
## Projects
### Project A
- Completed data analysis for client X."""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for no TODO"
            except ValidationError as e:
                assert "exactly one <TODO>" in str(e)
        
        def test_invalid_format(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Jane Smith - Data Scientist
Passionate about data and analytics.
## Projects
### Project A
- Completed data analysis for client X."""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for missing tagline marker"
            except ValidationError as e:
                assert "tagline" in str(e).lower()

        def test_content_before_subsection(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Jane Smith - Data Scientist
> <TODO>
## Projects
- Completed data analysis for client X.
### Project A"""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for content before subsection"
            except ValidationError as e:
                assert "before any subsection" in str(e)

        def test_subsection_before_section(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
### Project A
- <TODO>
## Projects"""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for subsection before section"
            except ValidationError as e:
                assert "before any section" in str(e)

        def test_invalid_line_format(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Jane Smith - Data Scientist
> Passionate about data and analytics.
## <TODO>
### Project A
* Completed data analysis for client X."""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for invalid bullet format (*)"
            except ValidationError as e:
                assert "Invalid line format" in str(e)

        def test_missing_title(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """> Passionate about data and analytics.
## <TODO>
### Project A
- Completed data analysis for client X."""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for missing title"
            except ValidationError as e:
                assert "title" in str(e).lower()

        def test_todo_not_alone_on_line(self):
            from doc_weaver.parser import load_markdown, ValidationError
            invalid_md = """# Title
> Tagline
## Section
### Sub
- hello <TODO> world"""
            try:
                _ = load_markdown(invalid_md, check_todo=True)
                assert False, "Should have raised ValidationError for TODO not alone on line"
            except ValidationError as e:
                assert "only non-markdown content" in str(e)