import * as http from "http";
import * as net from "net";
import * as path from "path";
import * as fs from "fs";
import * as vscode from "vscode";
import { ChildProcess, spawn } from "child_process";

let promptiniProcess: ChildProcess | undefined;
let currentPort: number | undefined;
let currentPanel: vscode.WebviewPanel | undefined;

// ── Prompt Library (persisted in globalState) ────────────────────────────────
interface LibraryEntry {
  id: string;
  prompt: string;
  model: string;
  status: string;
  date: string;
}

function getLibrary(ctx: vscode.ExtensionContext): LibraryEntry[] {
  return ctx.globalState.get<LibraryEntry[]>("promptiniLibrary", []);
}

function saveLibrary(ctx: vscode.ExtensionContext, lib: LibraryEntry[]) {
  ctx.globalState.update("promptiniLibrary", lib);
}

// ── Utility functions ────────────────────────────────────────────────────────
function canFileExist(filePath: string): Promise<boolean> {
  return new Promise((resolve) => {
    fs.access(filePath, fs.constants.F_OK, (err) => {
      resolve(!err);
    });
  });
}

function isPortAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close();
      resolve(true);
    });
    server.listen(port);
  });
}

async function findAvailablePort(startPort: number = 7860): Promise<number> {
  for (let port = startPort; port < startPort + 100; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error("Could not find an available port");
}

function waitForServer(port: number, timeoutMs: number): Promise<void> {
  const end = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.request({ host: "127.0.0.1", port, method: "GET", path: "/" }, (res) => {
        res.destroy();
        resolve();
      });

      request.on("error", () => {
        if (Date.now() >= end) {
          reject(new Error(`Server did not become available on port ${port} in ${timeoutMs}ms`));
        } else {
          setTimeout(check, 500);
        }
      });

      request.setTimeout(2000, () => {
        request.destroy();
      });
      request.end();
    };
    check();
  });
}

// ── Webview HTML with message bridge ─────────────────────────────────────────
function getWebviewHtml(url: string, mode: string): string {
  const base = url.replace(/\/+$/, "");
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; script-src 'unsafe-inline'; connect-src ${base};" />
<title>Promptini</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Noto+Naskh+Arabic:wght@400;500&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;}
  body{margin:0;padding:12px;background:#FAF9F6;color:#26221B;font-family:Inter,'Noto Naskh Arabic',system-ui,sans-serif;font-size:12px;}
  .hd{display:flex;align-items:center;gap:8px;margin-bottom:10px;}
  .logo{width:22px;height:22px;border-radius:6px;background:#F3EDE3;border:1px solid #E3D9C9;color:#92400E;display:flex;align-items:center;justify-content:center;font-size:12px;}
  .nm{font-size:13px;font-weight:700;letter-spacing:-.03em;} .nm span{color:#92400E;}
  .ver{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:#9A9284;}
  textarea{width:100%;height:78px;resize:none;border:1px solid rgba(226,216,199,.9);border-radius:10px;background:#fff;color:#26221B;padding:8px;font-family:Inter,'Noto Naskh Arabic',sans-serif;font-size:12px;line-height:1.55;margin-bottom:8px;}
  select{width:100%;appearance:none;border:1px solid rgba(226,216,199,.9);border-radius:10px;background:#fff;color:#26221B;padding:8px;font-size:12px;margin-bottom:8px;}
  .btn{width:100%;border-radius:10px;font-size:12px;font-weight:600;padding:10px;cursor:pointer;font-family:inherit;}
  .forge{background:#EFE9DF;border:1px solid #DED5C7;color:#2A2318;box-shadow:inset 0 1px 0 rgba(255,255,255,.7);}
  .forge:hover{background:#E7DFD2;}
  .lbl{display:flex;align-items:center;justify-content:space-between;margin:12px 0 6px;}
  .k{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:#9A9284;}
  .pill{display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:600;color:#9A9284;}
  .pill .dot{width:5px;height:5px;border-radius:50%;background:#C9CACE;}
  .pill.ready{color:#3F6212;} .pill.ready .dot{background:#65A30D;box-shadow:0 0 6px #65A30D;}
  .pill.eval{color:#92400E;} .pill.eval .dot{background:#B45309;}
  pre{margin:0 0 8px;min-height:130px;max-height:340px;overflow:auto;border:1px solid rgba(226,216,199,.9);border-radius:10px;background:#FCFBF9;color:#3A342A;padding:10px;font-family:'JetBrains Mono',monospace;font-size:11px;line-height:1.7;white-space:pre-wrap;}
  .copy{background:#fff;border:1px solid rgba(226,216,199,.9);color:#26221B;}
  .copy:hover{background:#FAF9F6;}
</style>
</head>
<body>
  <div class="hd"><div class="logo">&#9889;</div><div class="nm">Prompt<span>ini</span></div><div class="ver">v1.0</div></div>
  <textarea id="idea" dir="auto" placeholder="Rough idea…"></textarea>
  <select id="model">
    <option value="claude-code">Claude</option><option value="gpt-4">ChatGPT</option>
    <option value="gemini">Gemini</option><option value="cursor">Cursor</option>
    <option value="copilot">Copilot</option><option value="cline">Cline</option>
    <option value="deepseek">DeepSeek</option><option value="windsurf">Windsurf</option>
    <option value="general">Any</option>
  </select>
  <button class="btn forge" id="forge">&#9889; Promptini</button>
  <div class="lbl"><span class="k">Output</span><span class="pill" id="st"><span class="dot"></span>Idle</span></div>
  <pre id="out">Your optimized prompt will appear here.</pre>
  <button class="btn copy" id="copy">&#128203; Copy prompt</button>
<script>
  var API = "${base}";
  var idea=document.getElementById('idea'), out=document.getElementById('out'),
      forgeBtn=document.getElementById('forge'), copyBtn=document.getElementById('copy'),
      model=document.getElementById('model'), st=document.getElementById('st');
  function setSt(cls,label){ st.className='pill '+cls; st.innerHTML='<span class="dot"></span>'+label; }
  forgeBtn.addEventListener('click', function(){
    var p=(idea.value||'').trim(); if(!p) return;
    forgeBtn.disabled=true; forgeBtn.textContent='Optimizing…'; setSt('eval','Evaluating'); out.textContent='';
    fetch(API+'/forge',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:p,target_model:model.value,depth:'standard',language:'english'})})
      .then(function(r){return r.json();})
      .then(function(d){ if(d && d.transformed){ out.textContent=d.transformed; setSt('ready','Ready'); }
        else { out.textContent='⚠ '+((d&&d.error)||'failed'); setSt('','Error'); } })
      .catch(function(e){ out.textContent='⚠ '+e.message; setSt('','Error'); })
      .then(function(){ forgeBtn.disabled=false; forgeBtn.innerHTML='&#9889; Promptini'; });
  });
  copyBtn.addEventListener('click', function(){ var t=out.textContent||''; if(t) navigator.clipboard.writeText(t); });
</script>
</body>
</html>`;
}

// ── Python launcher ──────────────────────────────────────────────────────────
function choosePythonCommand(cwd?: string): string {
    // 1. Explicit override from settings.
    const configured = vscode.workspace.getConfiguration("promptini").get<string>("pythonPath");
    if (configured && fs.existsSync(configured)) {
        return configured;
    }
    // 2. A .venv inside the workspace.
    if (cwd) {
        const candidates = process.platform === "win32"
            ? [path.join(cwd, ".venv", "Scripts", "python.exe")]
            : [path.join(cwd, ".venv", "bin", "python3"), path.join(cwd, ".venv", "bin", "python")];
        for (const c of candidates) {
            if (fs.existsSync(c)) {
                return c;
            }
        }
    }
    // 3. System python.
    return process.platform === "win32" ? "python" : "python3";
}

function launchPromptini(cwd: string, port: number, output: vscode.OutputChannel): ChildProcess {
  const python = choosePythonCommand(cwd);
  const childProcess = spawn(python, ["-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", String(port)], {
    cwd,
    shell: false,
  });

  childProcess.stdout?.on("data", (chunk: Buffer) => {
    output.append(chunk.toString());
  });

  childProcess.stderr?.on("data", (chunk: Buffer) => {
    output.append(chunk.toString());
  });

  childProcess.on("exit", (code: number | null, signal: NodeJS.Signals | null) => {
    output.appendLine(`Promptini process exited with code=${code} signal=${signal}`);
    promptiniProcess = undefined;
  });

  return childProcess;
}

function stopPromptini(output: vscode.OutputChannel) {
  if (promptiniProcess && !promptiniProcess.killed) {
    output.appendLine("Stopping Promptini...");
    promptiniProcess.kill();
    promptiniProcess = undefined;
    currentPort = undefined;
  }
  if (currentPanel) {
    currentPanel.dispose();
    currentPanel = undefined;
  }
}

// ── Message handler (shared between sidebar and panel) ───────────────────────
function setupMessageHandler(
  webview: vscode.Webview,
  context: vscode.ExtensionContext
) {
  webview.onDidReceiveMessage((message: any) => {
    switch (message.type) {
      case "copyText": {
        if (message.text) {
          vscode.env.clipboard.writeText(message.text).then(() => {
            vscode.window.showInformationMessage("📋 Prompt copied to clipboard!");
          });
        }
        break;
      }
      case "savePrompt": {
        if (message.entry) {
          const lib = getLibrary(context);
          const entry: LibraryEntry = {
            id: Date.now().toString(),
            prompt: message.entry.prompt || "",
            model: message.entry.model || "unknown",
            status: message.entry.status || "",
            date: new Date().toISOString(),
          };
          lib.unshift(entry);
          saveLibrary(context, lib);
          vscode.window.showInformationMessage("⭐ Prompt saved to library!");
          // Sync back to webview
          webview.postMessage({ type: "syncLibrary", library: lib });
        }
        break;
      }
      case "ready": {
        const lib = getLibrary(context);
        webview.postMessage({ type: "syncLibrary", library: lib });
        break;
      }
    }
  });
}

// ── Sidebar WebviewViewProvider ──────────────────────────────────────────────
class PromptiniSidebarProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "promptiniView";
  private _view?: vscode.WebviewView;

  constructor(private readonly _context: vscode.ExtensionContext) {}

  resolveWebviewView(webviewView: vscode.WebviewView) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
    };

    const config = vscode.workspace.getConfiguration("promptini");
    const hfUrl = config.get<string>("hfUrl") || "https://becher-zribi-prompt-forge-rag.hf.space";
    
    webviewView.webview.html = getWebviewHtml(hfUrl, "cloud");
    setupMessageHandler(webviewView.webview, this._context);
  }

  public sendPrompt(text: string) {
    if (this._view) {
      this._view.webview.postMessage({ type: "setPrompt", text });
    }
  }
}

// ── Activation ──────────────────────────────────────────────────────────────
export function activate(context: vscode.ExtensionContext) {
  const output = vscode.window.createOutputChannel("Promptini Server");

  // Register sidebar provider
  const sidebarProvider = new PromptiniSidebarProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      PromptiniSidebarProvider.viewType,
      sidebarProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  // "Open App" command — opens in a full editor panel
  const openCommand = vscode.commands.registerCommand("promptini.open", async () => {
    if (currentPanel) {
      currentPanel.reveal(vscode.ViewColumn.One);
    } else {
      currentPanel = vscode.window.createWebviewPanel("promptini", "Promptini", vscode.ViewColumn.One, {
        enableScripts: true,
        retainContextWhenHidden: true,
      });

      currentPanel.onDidDispose(() => {
        currentPanel = undefined;
      });
    }

    const config = vscode.workspace.getConfiguration("promptini");
    const mode = config.get<string>("mode") || "cloud";
    const hfUrl = config.get<string>("hfUrl") || "https://becher-zribi-prompt-forge-rag.hf.space";

    if (mode === "cloud") {
      output.appendLine(`Opening Cloud Mode: ${hfUrl}`);
      currentPanel.webview.html = getWebviewHtml(hfUrl, "cloud");
      setupMessageHandler(currentPanel.webview, context);
    } else {
      const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
      if (!workspaceFolder) {
        vscode.window.showErrorMessage("Open a workspace folder before launching Promptini.");
        return;
      }

      const workspaceRoot = workspaceFolder.uri.fsPath;
      const appPath = path.join(workspaceRoot, "api.py");

      if (!(await canFileExist(appPath))) {
        vscode.window.showErrorMessage("Could not find api.py in the workspace root.");
        return;
      }

      if (promptiniProcess && !promptiniProcess.killed) {
        stopPromptini(output);
      }

      output.show(true);
      output.appendLine("Starting Promptini Python server...");

      let port = 7860;
      try {
        port = await findAvailablePort();
        output.appendLine(`Using port ${port}`);
      } catch (err) {
        vscode.window.showErrorMessage(`Could not find an available port: ${err instanceof Error ? err.message : err}`);
        return;
      }

      promptiniProcess = launchPromptini(workspaceRoot, port, output);

      try {
        await waitForServer(port, 120000);
      } catch (err) {
        vscode.window.showErrorMessage(`Promptini did not start in time: ${err instanceof Error ? err.message : err}`);
        return;
      }

      currentPort = port;
      currentPanel.webview.html = getWebviewHtml(`http://127.0.0.1:${port}/`, "local");
      setupMessageHandler(currentPanel.webview, context);
      vscode.window.showInformationMessage(`Promptini is ready on port ${port}`);
    }
  });

  // "Optimize Selection" command — sends selected text to the sidebar
  const forgeSelectionCmd = vscode.commands.registerCommand("promptini.optimizeSelection", () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    const selection = editor.document.getText(editor.selection);
    if (selection) {
      sidebarProvider.sendPrompt(selection);
      vscode.window.showInformationMessage("Text sent to Promptini sidebar.");
    }
  });

  const stopCommand = vscode.commands.registerCommand("promptini.stop", async () => {
    stopPromptini(output);
    output.appendLine("Promptini stopped.");
    vscode.window.showInformationMessage("Promptini has been stopped.");
  });

  // "Optimize Selection via API" — calls the local FastAPI engine (api.py)
  const forgeApiCmd = vscode.commands.registerCommand("promptini.optimizeSelectionApi", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) { return; }
    const selection = editor.document.getText(editor.selection);
    if (!selection) {
      vscode.window.showWarningMessage("Select some text to optimize first.");
      return;
    }
    const cfg = vscode.workspace.getConfiguration("promptini");
    const base = (cfg.get<string>("apiUrl") || "http://127.0.0.1:8000").replace(/\/$/, "");
    const targetModel = cfg.get<string>("apiModel") || "general";
    const fetchFn: any = (globalThis as any).fetch;
    try {
      const result = await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "Promptini: optimizing via API…" },
        async () => {
          const r = await fetchFn(`${base}/forge`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: selection, target_model: targetModel, depth: "standard", language: "english" }),
          });
          if (!r.ok) { throw new Error(`HTTP ${r.status}`); }
          return await r.json();
        }
      );
      const transformed = result && result.transformed;
      if (!transformed) {
        vscode.window.showErrorMessage("Promptini API returned no prompt.");
        return;
      }
      await editor.edit((ed) => ed.replace(editor.selection, transformed));
      vscode.window.showInformationMessage("✨ Prompt optimized via API.");
    } catch (err: any) {
      vscode.window.showErrorMessage(
        `Promptini API error: ${err?.message ?? err}. Is the engine running (uvicorn api:app)?`
      );
    }
  });

  context.subscriptions.push(openCommand, stopCommand, forgeSelectionCmd, forgeApiCmd);
}

export function deactivate() {
  if (promptiniProcess && !promptiniProcess.killed) {
    promptiniProcess.kill();
    promptiniProcess = undefined;
  }
}
