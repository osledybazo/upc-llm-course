import re, pathlib, markdown
here = pathlib.Path(__file__).parent
md = (here / "report.md").read_text()
ex2 = (here.parent / "exercise2/outputs.md").read_text()
ex2 = re.sub(r"^## ", "### ", ex2, flags=re.M)
md = md.replace("{{EX2_OUTPUTS}}", ex2)
body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
css = """body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:10.5pt;line-height:1.45;max-width:800px;margin:auto;color:#111}
h1{font-size:20pt;margin-bottom:4px}h2{font-size:15pt;border-bottom:1px solid #ccc;padding-bottom:3px;margin-top:28px;page-break-before:auto}
h3{font-size:11.5pt;margin-top:16px}pre{background:#f5f5f5;padding:8px;border-radius:4px;white-space:pre-wrap;word-break:break-word;font-size:8.5pt}
code{font-family:Menlo,monospace;font-size:9pt}table{border-collapse:collapse;margin:8px 0}td,th{border:1px solid #bbb;padding:4px 8px;font-size:9.5pt;vertical-align:top}
th{background:#eee}hr{border:0;border-top:1px solid #ddd;margin:20px 0}"""
(here / "report.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>W1 Ex1-4 Report</title><style>{css}</style></head><body>{body}</body></html>")
