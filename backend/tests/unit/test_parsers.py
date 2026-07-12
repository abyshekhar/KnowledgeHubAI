from pathlib import Path
from backend.app.infrastructure.documents.parsers import DocumentParser

def test_parse_txt_success(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello World this is a text file", encoding="utf-8")
    
    parser = DocumentParser()
    pages = parser.parse(txt_file)
    assert len(pages) == 1
    assert pages[0].text == "Hello World this is a text file"
    assert pages[0].page_number is None

def test_parse_csv_success(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_content = "Name,Age,Role\nAlice,30,Engineer\nBob,25,Designer\n"
    csv_file.write_text(csv_content, encoding="utf-8")
    
    parser = DocumentParser()
    pages = parser.parse(csv_file)
    assert len(pages) == 2
    assert pages[0].text == "Name: Alice, Age: 30, Role: Engineer"
    assert pages[0].page_number == 1
    assert pages[1].text == "Name: Bob, Age: 25, Role: Designer"
    assert pages[1].page_number == 2
