# jev-minesweeper-harness

Jev System One tester + hex playables.

## Play in a browser (no build)

After clone, open these files:

- `public/hold.html` — **Tower defense**: place walls (maze) and towers, send waves that walk the shortest S→B path.
- `public/hexops.html` — mines + resource camps + simpler hold, one page.
- `public/kinfield.html` — inverse mines: place related colors so printed k holds.
- `public/index.html` — directory.

## Jev CLI

```bash
pip install -r requirements.txt
python -m harness.cli --world hex --preset hex-tiny --mode mock --games 10
python -m harness.cli --world minesweeper --mode mock --games 10
python -m harness.cli --world generic --spec examples/ticket_triage.json
```

`--mode jev` needs `TYPESAFE_API_KEY`.

## Layout

```
harness/cli.py           run loop
jev_client/              TypeSafe decide + mock
worlds/minesweeper.py    square mines
worlds/hex_minesweeper.py cube q,r,s mines
worlds/generic.py        any JSON state
public/hold.html         TD engine
public/hexops.html       3-mode SPWA
public/kinfield.html     inverse kinship puzzle
```

Lattice matches SoMaCoSF/hex-map-wfc cube coords.
