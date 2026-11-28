"""Build the one-page W2-Ex1 report: report_ex1.md -> report_ex1.html -> W2-Ex1_Osledy_Bazo.pdf (headless Chrome)."""
import pathlib, subprocess, markdown
here = pathlib.Path(__file__).parent
css = """@page{size:A4;margin:12mm 14mm}body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:9.2pt;line-height:1.35;color:#111;margin:0}
h1{font-size:15pt;margin:0 0 4px}p{margin:5px 0}pre{background:#f5f5f5;padding:5px 8px;border-radius:4px;white-space:pre-wrap;font-size:7.6pt;line-height:1.3;margin:4px 0}
code{font-family:Menlo,monospace;font-size:8pt}img{width:100%;border:1px solid #ccc;border-radius:4px;display:block;margin:3px 0 6px}"""
body = markdown.markdown((here / "report_ex1.md").read_text(), extensions=["fenced_code", "sane_lists"])
html = here / "report_ex1.html"
html.write_text(f"<!doctype html><html><head><meta charset='utf-8'><title>W2 Ex1 Report</title><style>{css}</style></head><body>{body}</body></html>")
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless", "--disable-gpu",
                "--no-pdf-header-footer", f"--print-to-pdf={here / 'W2-Ex1_Osledy_Bazo.pdf'}", html.as_uri()], check=True)
