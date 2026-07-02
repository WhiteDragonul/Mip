# MIP robot — piese pentru print 3D și asamblare

Corp robot desktop, **~200 mm înălțime**, gol în interior pentru electronică.
Toate piesele sunt solide *watertight* (gata de slicer). Generate cu
[`tools/make_robot_parts.py`](../../tools/make_robot_parts.py) — modifică
parametrii și rulează din nou oricând.

Forma urmează **robotul alb din poza de referință** (cap rotunjit-cub cu ecran
inset + ramă albă, buton rotund lateral, corp ou, brațe scurte, picioare subțiri
cu tălpi ovale). Fără fundiță.

## Lista pieselor (10 fișiere `.stl`)

| Fișier | Ce e | Câte printezi |
|---|---|---|
| `head.stl` | Capul (rotunjit-cub, gol, fereastră ecran, **gaură cameră** sus, **2 urechi**, găuri cablu) | 1 |
| `face_bezel.stl` | Panoul negru al feței care fixează display-ul | 1 |
| `body.stl` | Pieptul ou (gol — Pi + fan + baterie), socluri umeri/gât/șold | 1 |
| `back_panel.stl` | Capac spate curbat (la nivel) + **grilă difuzor** (găuri) | 1 |
| `arm_left/right.stl` | Brațele lungi (~cât tot corpul, cu bilă la umăr) | 1 + 1 |
| `leg_left/right.stl` | Picioarele subțiri (peg la șold, bilă la gleznă) | 1 + 1 |
| `foot_left/right.stl` | Tălpile ovale (cuib bilă la gleznă) | 1 + 1 |

## Cum se îmbină (mos-baba / snap)

- **Umeri** — *bilă-cuib*: împingi bila brațului în cuibul corpului → face clic și
  se rotește liber. Iese doar trasă tare. (Cuibul are fante = „zimții" care flexează.)
- **Glezne** — *bilă-cuib*: bila de jos a piciorului intră în talpă; talpa se
  înclină în orice direcție (acoperă și mișcarea de la călcâi/vârf).
- **Gât și șolduri** — *peg cu cheie + barbă*: peg-ul intră drept, are o latură
  plată (anti-rotație) și un inel-barbă care trece de un șanț → rămâne fix, se
  scoate trăgând. Picioarele rămân **drepte/rigide** la șold (cum ai cerut).
- **Capacul spate** — intră în deschiderea din spate cu 4 cleme (presfit/lipit).

## Electronica (intern)

- **Piept (`body`)**: Raspberry Pi 3/4 (85×56) montat vertical pe peretele din
  spate + fan + baterie în față. Acces prin `back_panel`.
- **Cap (`head`)**: display 2.4" IPS (modul 70.5×43.3) se așază din **față** în
  prag, ținut de `face_bezel`. Cablul trece prin gâtul gol în piept.
  **Camera** se montează în spatele găurii Ø7 de deasupra ecranului (neacoperită
  de ramă). **Difuzorul** stă în spate, în spatele grilei de găuri din `back_panel`.

## Setări de print recomandate (FDM)

- Material: **PLA** sau **PETG**, strat 0.2 mm.
- Pereți: 3 perimetre, umplere 15–20%.
- **Suporturi**: DA pentru `head` (interior + fereastră) și `body` (socluri
  umeri, deschidere spate). Restul fără.
- Orientare: capul cu fața în sus; corpul cu gâtul în sus; brațele/picioarele pe lung.

## Reglarea îmbinărilor (IMPORTANT)

Toleranțele sunt setate pentru o imprimantă FDM tipică:
`CLR_BALL=0.35`, `CLR_PEG=0.30`, `CLR_HINGE=0.40` mm (sus în script).

Printează **întâi un singur picior + talpă** ca test. Dacă bila intră prea greu,
mărește `CLR_BALL`; dacă e prea slab, micșorează-l — apoi regenerează.

## Vizualizare

- Tot ansamblul într-un fișier: [`../robot_assembly.obj`](../robot_assembly.obj)
- Imagine de ansamblu: [`../parts_preview.png`](../parts_preview.png)
