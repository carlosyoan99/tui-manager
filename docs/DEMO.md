# Guion de demo visual (2.0.2)

Demo corta de **TUI Manager 2.0.2** con [`vhs`](https://github.com/charmbracelet/vhs) o
[`asciinema`](https://asciinema.org/). Objetivo: 60–90 s mostrando el menú, paquetes,
procesos, temas, catálogo y la ayuda. **Los comandos son sugerencias; no se han
ejecutado para escribir este documento** (no hay herramientas de grabación en el
entorno de desarrollo).

## Antes de grabar

- Terminal de al menos **120 × 32**; fuente monoespaciada y tema legible.
- `tm --version` → `tui-manager 2.0.2` y `tm --doctor` sin avisos falsos.
- Grabar en entorno desechable (VM/contenedor). Si aparece confirmación de
  `sudo`, pulsa `n` y narra que se canceló. No ejecutar instalaciones reales.
- Evitar datos personales: *Acerca de* muestra usuario, host y rutas.
- No subir la grabación a ningún servicio sin decidirlo explícitamente.

## Mapa de teclas

| Pantalla | Tecla | Acción |
|---|---|---|
| Menú | `[1]`–`[9]`, `[0]` | Abrir entrada (10ª = catálogo) |
| Cualquiera | `?` | Ayuda contextual (incluye licencia MIT y GitHub) |
| Aplicaciones | `Espacio` | Marcar para acción por lote |
| Procesos | `s` | Ciclar orden (cpu/mem/usuario/nombre/PID) |
| Temas | `R` / `L` | Wallpaper aleatorio / pack desde carpeta local |
| Ajustes | `s` | Snapshots (crear/restaurar) |
| Catálogo | `w` | Webapps (si disponible en la build) |

## Tape `vhs` (guardar como `demo.tape` y ejecutar `vhs demo.tape`)

```hcl
Output demo.gif
Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 800
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

Type "tm --version" Enter
Sleep 1s
Type "tm --doctor" Enter
Sleep 2s
Type "tm --quickstart" Enter
Sleep 2s
Type "tm" Enter
Sleep 3s

# Menú y aplicaciones
Type "1" Enter
Sleep 2s
Down
Type " "
Down
Type " "
Sleep 1s
Type "?"
Sleep 1s
Escape
Escape
Sleep 1s

# Procesos y orden
Type "2" Enter
Sleep 2s
Type "s"
Sleep 1s
Type "s"
Sleep 1s
Escape

# Temas y catálogo
Type "4" Enter
Sleep 2s
Type "R"
Sleep 1s
Escape
Type "0" Enter
Sleep 2s
Escape

# Ayuda (licencia + GitHub)
Type "7" Enter
Sleep 2s
Escape
Type "q" Enter
```

## Alternativa con asciinema

```bash
asciinema rec -c "tm" --title "TUI Manager 2.0.2" demo.cast
# reproduce con: asciinema play demo.cast
```

## Checklist antes de publicar la grabación

- [ ] No aparece correo personal ni dato sensible.
- [ ] Confirmaciones de `sudo` canceladas (`n`).
- [ ] `--doctor` no muestra avisos falsos (solo la CLI de la distro).
- [ ] Ayuda muestra licencia MIT y GitHub del proyecto.
- [ ] Duración 60–90 s y texto legible a 1200 px.
