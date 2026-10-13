# Codex Island

Independent Linux Python/Tk desktop application. Run commands from this directory.
Use the standard library; no root installs or shared supervisor changes.

- Codex owns authentication, sandboxing, and conversation storage. Never read its credential files.
- Embed the native GTK3/VTE terminal over X11. Default Launch to Codex CLI,
  with no shell interpolation. Keep helper stdio restricted to lifecycle metadata
  and focus/resize controls. Never expose a network control API.
- Ctrl+C belongs to the terminal. Do not add terminal Stop/Interrupt controls or
  close a live Codex session automatically. Require manual exit before closing.
- The private notify socket accepts completion metadata only. Never relay
  prompts or assistant messages through it or persist terminal contents.
- Tk widgets are main-thread only; background results travel through a queue.
- Never use shell=True or construct shell commands from user input.
- Docker controls target a fixed local Unix socket, never the current Docker context.
- Only stop explicitly selected, confirmed services. Port process signals require pidfds, same-user ownership, start-time revalidation, and a fresh listener check. Protect the app, ancestors, and its Codex process tree.
- Never store transcripts, environment values, service logs, or tokens in this app.

Validation: `python3 -m unittest discover -s tests -v`, `python3 -m py_compile island.py runtime.py`.
