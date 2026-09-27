from dotenv import load_dotenv
load_dotenv()

import gradio as gr

from llm import transform_prompt
from scorer import pick_best
from core.tasks import detect_task_type
from core.concurrency import map_ordered
from core.config import get_settings
from core.ratelimit import RateLimiter

BEST_OF = 3

_settings = get_settings()
_LIMITER = RateLimiter(_settings.rate_limit_calls, _settings.rate_limit_window)

EMPTY_PILL = '<span class="pf-eval"><span class="dot" style="animation:none"></span>Idle</span>'
EVAL_PILL  = '<span class="pf-eval"><span class="dot"></span>Evaluating</span>'
READY_PILL = '<span class="pf-ready"><span class="dot"></span>✓ Ready</span>'

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Naskh+Arabic:wght@400;500&display=swap');
:root{
  --bg:#FAF9F6; --ink:#26221B; --soft:#6B6558; --muted:#9A9284;
  --line:#E8E2D6; --line2:#E3D9C9; --amber:#92400E; --olive:#65A30D; --olive-ink:#3F6212;
  --panel:#FFFFFF; --creambtn:#EFE9DF; --creambtn-b:#DED5C7; --creambtn-ink:#2A2318; --radius:16px;
}
*{box-sizing:border-box;}
body,.gradio-container,.app,.main,.wrap{background:#FAF9F6!important;color:var(--ink)!important;
  font-family:'Inter','Noto Naskh Arabic',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif!important;-webkit-font-smoothing:antialiased;}
.gradio-container{max-width:100%!important;margin:0!important;padding:14px 40px 52px!important;
  --primary-400:#CBBBA4;--primary-500:#B99E7F;--primary-600:#92400E;--color-accent:#B99E7F;--color-accent-soft:#EFE9DF;--loader-color:#CBBBA4;}
footer,.footer{display:none!important;}
.gradio-container .block,.gradio-container .form{border:none!important;background:transparent!important;box-shadow:none!important;}
button,input,select,textarea,label,span,div,h1,h2,p{font-family:'Inter','Noto Naskh Arabic',sans-serif!important;}
.pf-output textarea,.pf-count,.pf-tok{font-family:'JetBrains Mono',ui-monospace,monospace!important;}
@keyframes epPulse{0%,100%{opacity:1}50%{opacity:.4}}

.pf-head{display:flex;flex-direction:column;align-items:center;gap:8px;padding:8px 0 20px;border-bottom:1px solid var(--line);margin-bottom:14px;}
.pf-brandline{display:flex;align-items:center;gap:12px;}
.pf-logo{width:40px;height:40px;border-radius:12px;background:#F3EDE3;border:1px solid var(--line2);color:var(--amber);
  display:flex;align-items:center;justify-content:center;font-size:18px;}
.pf-brand{font-size:32px;font-weight:700;letter-spacing:-.045em;color:var(--ink);}
.pf-brand span{color:var(--amber);}
.pf-tag{margin:0;font-size:14px;color:var(--soft);text-align:center;max-width:600px;}

.pf-panel{background:var(--panel)!important;border:1px solid var(--line)!important;border-radius:var(--radius)!important;
  box-shadow:0 1px 2px rgba(42,35,24,.04)!important;padding:22px!important;}
.pf-rowhead{display:flex;align-items:center;justify-content:space-between;gap:10px;}
.pf-label{margin:0;font-size:11px;font-weight:600;letter-spacing:.10em;text-transform:uppercase;color:var(--soft);}
.pf-count{font-size:11px;color:var(--muted);}
.pf-flabel{font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px;}

.pf-ready,.pf-eval{display:inline-flex;align-items:center;gap:8px;font-size:11px;font-weight:600;border-radius:999px;padding:4px 12px;}
.pf-ready{color:var(--olive-ink);border:1px solid rgba(101,163,13,.28);background:rgba(101,163,13,.08);}
.pf-ready .dot{width:6px;height:6px;border-radius:50%;background:var(--olive);}
.pf-eval{color:var(--soft);border:1px solid var(--creambtn-b);background:var(--creambtn);}
.pf-eval .dot{width:6px;height:6px;border-radius:50%;background:#B99E7F;animation:epPulse 1.1s ease-in-out infinite;}

textarea,input[type=text]{border:1px solid var(--line)!important;border-radius:12px!important;background:#FFFFFF!important;
  color:var(--ink)!important;font-size:15px!important;line-height:1.75!important;}
textarea:focus,input:focus{outline:none!important;border-color:rgba(146,64,14,.35)!important;box-shadow:0 0 0 2px rgba(146,64,14,.16)!important;}

/* dropdowns — white, thin border, no blue chips (labels are our own HTML) */
.pf-ctl input,.pf-ctl .wrap,.pf-ctl .secondary-wrap,.pf-ctl .container{background:#FFFFFF!important;
  border:1px solid var(--line)!important;border-radius:12px!important;font-size:13px!important;color:var(--ink)!important;box-shadow:none!important;}

.pf-forge,.pf-forge button,button.pf-forge{background:var(--creambtn)!important;color:var(--creambtn-ink)!important;
  border:1px solid var(--creambtn-b)!important;border-radius:12px!important;font-size:14px!important;font-weight:600!important;
  padding:15px!important;width:100%!important;box-shadow:none!important;transition:background .18s;}
.pf-forge button:hover,button.pf-forge:hover{background:#E7DFD2!important;}

.pf-copy,.pf-copy button,button.pf-copy{background:#FFFFFF!important;color:var(--ink)!important;
  border:1px solid var(--line)!important;border-radius:12px!important;font-size:13px!important;font-weight:600!important;
  padding:12px 16px!important;width:100%!important;box-shadow:none!important;transition:background .18s;}
.pf-copy button:hover,button.pf-copy:hover{background:#FAF9F6!important;}

/* single output card */
.pf-output textarea{border:1px solid var(--line)!important;border-radius:12px!important;background:#FCFBF9!important;
  font-size:13px!important;line-height:1.8!important;color:#3A342A!important;padding:16px!important;}
.pf-output textarea:focus{box-shadow:none!important;border-color:var(--line)!important;}
.pf-tok{font-size:11px;color:var(--muted);}
"""

COPY_JS = "(t)=>{ if(!t) return; navigator.clipboard.writeText(t).then(()=>{ if(window.pfToast) window.pfToast('Copied to clipboard'); }); }"

INIT_JS = """
() => {
  window.pfToast = (m) => {
    let r=document.getElementById('pf-toast');
    if(!r){ r=document.createElement('div'); r.id='pf-toast';
      r.style.cssText='position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:9999;';
      document.body.appendChild(r); }
    const t=document.createElement('div'); t.textContent=m;
    t.style.cssText='background:#26221B;color:#fff;padding:9px 16px;border-radius:10px;font-size:13px;font-family:Inter,sans-serif;';
    r.appendChild(t); setTimeout(()=>t.remove(),1700);
  };
  const wire=()=>{ const rw=document.querySelector('#pf-raw textarea'), cc=document.getElementById('pf-charcount');
    if(rw&&cc&&!rw._c){rw._c=true;const u=()=>cc.textContent=rw.value.length+' chars';rw.addEventListener('input',u);u();} };
  wire(); setTimeout(wire,600); setTimeout(wire,1500);
}
"""

_LANG_MAP = {"Auto": "auto", "English": "english", "Arabic": "arabic", "Derja": "derja", "Français": "french"}

def forge(raw_prompt, model, depth, language, request: gr.Request | None = None):
    if not raw_prompt or not raw_prompt.strip():
        yield "", EMPTY_PILL, ""
        return
    client_id = request.client.host if (request and request.client) else "anon"
    if not _LIMITER.allow(client_id):
        yield "", '<span class="pf-eval"><span class="dot"></span>Slow down</span>', ""
        return
    yield "", EVAL_PILL, '<span class="pf-tok">evaluating…</span>'
    task_type = detect_task_type(raw_prompt)
    lang = _LANG_MAP.get(language, "english") if isinstance(language, str) else "english"

    def _gen(_i):
        try:
            txt, _p, _u = transform_prompt(raw_prompt, model, task_type, depth, [], lang, False)
            return (txt or "").strip()
        except Exception as e:
            return f"__ERR__{e}"

    results = map_ordered(_gen, list(range(BEST_OF)), max_workers=BEST_OF)
    cands = [r for r in results if r and not r.startswith("__ERR__")]
    if not cands:
        err = next((r[7:] for r in results if r.startswith("__ERR__")), "generation failed")
        yield "", '<span class="pf-eval"><span class="dot"></span>Error</span>', f'<span class="pf-tok">{err[:60]}</span>'
        return
    best = cands[pick_best(raw_prompt, cands, model) if len(cands) > 1 else 0]
    task_badge = task_type.replace("_", " ").title()
    yield best, READY_PILL, f'<span class="pf-tok">{task_badge} · ~{max(1, len(best)//4)} tokens</span>'

with gr.Blocks(title="Promptini") as demo:
    gr.HTML("""
<div class="pf-head">
  <div class="pf-brandline"><div class="pf-logo">⚡</div><div class="pf-brand">Prompt<span>ini</span></div></div>
  <p class="pf-tag">Turn a rough idea in Tunisian Derja, Arabic, French, or English into a clean, model-ready prompt.</p>
</div>
""")

    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=420, elem_classes="pf-panel"):
            gr.HTML('<div class="pf-rowhead"><span class="pf-label">Raw input</span><span class="pf-count" id="pf-charcount">0 chars</span></div>')
            raw_input = gr.Textbox(show_label=False, elem_id="pf-raw", container=False,
                                   placeholder="3andi API Flask, n7eb endpoint yraja3 les users…", lines=9)
            with gr.Row(elem_classes="pf-ctl", equal_height=True):
                with gr.Column(min_width=0):
                    gr.HTML('<div class="pf-flabel">Model</div>')
                    model_dropdown = gr.Dropdown(
                        [("Claude Code", "claude-code"), ("Claude", "claude"), ("ChatGPT", "gpt-4"),
                         ("Gemini", "gemini"), ("Cursor", "cursor"), ("Cline", "cline"),
                         ("Aider", "aider"), ("Copilot", "copilot"), ("DeepSeek", "deepseek"),
                         ("Windsurf", "windsurf"), ("Any", "general")],
                        value="claude-code", show_label=False, container=False, elem_id="pf-model")
                with gr.Column(min_width=0):
                    gr.HTML('<div class="pf-flabel">Depth</div>')
                    depth_dropdown = gr.Dropdown(
                        [("Balanced", "standard"), ("Concise", "concise"), ("Detailed", "comprehensive")],
                        value="standard", show_label=False, container=False, elem_id="pf-depth")
                with gr.Column(min_width=0):
                    gr.HTML('<div class="pf-flabel">Language</div>')
                    language_dropdown = gr.Dropdown(
                        ["English", "Auto", "Arabic", "Derja", "Français"],
                        value="English", show_label=False, container=False, elem_id="pf-lang")
            forge_btn = gr.Button("⚡ Promptini", elem_classes="pf-forge")

        with gr.Column(scale=1, min_width=420, elem_classes="pf-panel"):
            with gr.Row(elem_classes="pf-rowhead"):
                status = gr.HTML(EMPTY_PILL)
                gr.HTML('<span class="pf-label">Optimized structure</span>')
            output = gr.Textbox(show_label=False, container=False, lines=16, interactive=True,
                                elem_classes="pf-output", placeholder="Your optimized prompt will appear here.")
            with gr.Row(elem_classes="pf-rowhead"):
                tokens = gr.HTML('<span class="pf-tok">—</span>')
                copy_btn = gr.Button("📋 Copy prompt", elem_classes="pf-copy")

    forge_btn.click(fn=forge, inputs=[raw_input, model_dropdown, depth_dropdown, language_dropdown],
                    outputs=[output, status, tokens])
    copy_btn.click(fn=None, inputs=output, js=COPY_JS)
    demo.load(None, None, None, js=INIT_JS)

if __name__ == "__main__":
    demo.queue().launch(css=CSS, theme=gr.themes.Soft(), ssr_mode=False)
