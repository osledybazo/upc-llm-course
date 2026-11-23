import pathlib, re, markdown
here = pathlib.Path(__file__).parent
src = (here / "build.py").read_text()
css = re.search(r'css = """(.*?)"""', src, re.S).group(1) + "img{max-width:100%;border:1px solid #ccc;border-radius:4px}"
body = markdown.markdown((here / "report_ex5.md").read_text(), extensions=["tables", "fenced_code", "sane_lists"])
(here / "report_ex5.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>W1 Ex5 Report</title><style>{css}</style></head><body>{body}</body></html>")
