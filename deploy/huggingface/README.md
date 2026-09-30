---
title: F1 Race Control
emoji: 🏎️
colorFrom: purple
colorTo: red
sdk: docker
app_port: 7860
pinned: false
short_description: F1 telemetry, race replay and strategy simulation
---

# F1 Race Control

Lap-vs-lap FastF1 telemetry, a pit-wall race replay, and Monte Carlo race
strategy simulation.

This Space is deployed automatically from GitHub; the source, docs and issue
tracker live there. The first load of a race downloads its data from FastF1
and can take up to a minute; after that it's cached until the Space restarts.
