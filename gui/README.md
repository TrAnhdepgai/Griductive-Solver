# Griductive GUI

Run the browser UI against the team's Python engine from the repository root:

```bash
python -m src.engine.gui_server
```

Open <http://127.0.0.1:8001>. The daily cards, verdict calls, hints, single
agent steps, auto solve, and restart use the repository puzzles and
`LocalGameEngine` / `LogicAgent`. The browser does not receive hidden solution
statuses or unrevealed clues. Embedded demo puzzle data has been removed, and
the game controls now use the backend API instead of the former mock solver.
