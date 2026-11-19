# Guion de demo visual

Guion para grabar una demostración corta de **TUI Manager 1.1.0** con
[`vhs`](https://github.com/charmbracelet/vhs) o
[`asciinema`](https://asciinema.org/). **Los comandos de esta guía son
sugerencias: no se han ejecutado al escribir este documento.**

La demo muestra, en este orden: arranque, menú con atajos, instalación de un
paquete, búsqueda, procesos y pantalla *Acerca de*. Duración objetivo: **60–90
segundos**.

## Antes de grabar

- Terminal de al menos **100 columnas × 30 filas**; usa una fuente
  monoespaciada y un tema legible (One Dark, Nord o similar).
- Tener `tui-manager` instalado y accesible en el `PATH`:
  `python -m pip install -e .` desde la raíz del repo.
- Comprobar antes con `tui-manager --version` y `tui-manager --doctor`.
- **Grabar en un entorno desechable** (VM o contenedor). El paso de
  instalación puede requerir `sudo` y modificar el sistema; si grabas en tu
  equipo habitual, pulsa `n` en la confirmación y narra que se ha cancelado.
- Evita mostrar datos personales: la pantalla *Acerca de* incluye usuario,
  nombre de host y rutas.
- No subas la grabación a ningún servicio sin decidirlo explícitamente antes.

## Mapa de teclas de la demo

| Pantalla | Tecla | Acción |
|---|---|---|
| Menú principal | `1` … `9`, `0` | Abre la entrada numerada (10ª = `0`) |
| Menú principal | `?` | Ayuda contextual |
| Menú principal | `Esc` / `q` | Salir |
| Paquetes | `f` o `/` | Buscar / filtrar |
| Paquetes | `i` | Instalar el paquete seleccionado |
| Paquetes | `c` | Actualizar caché de repositorios |
| Paquetes | `u` | Ver detalles |
| Procesos | `s` | Cambiar criterio de orden (CPU, RAM, usuario, nombre, PID) |
| Procesos | `f` o `/` | Filtrar |
| Procesos | `k` / `K` | Terminar / terminar con SIGKILL |
| Procesos | `p` | Pausar la actualización en vivo |
| Procesos | `Esc` | Volver al menú |

Las diez entradas del menú son: `1` Paquetes, `2` Procesos, `3` Sistema,
`4` Temas, `5` Actualizar, `6` Ajustes, `7` Ayuda, `8` Acerca de, `9` Logs y
`0` Catálogo de apps.

## Secuencias

### 1. Arranque (0:00–0:10)

```text
tui-manager --version
tui-manager
```

Enfocar el momento en que aparece el menú con el encabezado y la barra de
atajos. Narra: «TUI Manager es un panel portátil para la terminal: Linux, BSD
y Termux».

### 2. Menú con atajos (0:10–0:25)

Con el menú principal abierto:

```text
?       -> ayuda contextual
Esc     -> cerrar la ayuda
2       -> Procesos
Esc     -> volver al menú
0       -> Catálogo de apps (179 apps en 29 categorías)
Esc     -> volver al menú
```

Narra que toda la navegación es por teclado y que las entradas no soportadas
por el entorno aparecen deshabilitadas con su motivo.

### 3. Instalar paquete (0:25–0:45)

En un entorno desechable, con `sudo` ya resuelto:

```text
1       -> Paquetes
c       -> actualizar caché (opcional; puedes omitirlo para acortar)
f       -> buscar
"htop"  -> escribir el nombre
Enter   -> cerrar el campo de búsqueda
u       -> ver detalles del paquete seleccionado
Esc     -> volver a la lista
i       -> instalar
y       -> confirmar (usa 'n' si no quieres modificar el sistema)
Esc     -> volver al menú principal
```

Si la confirmación pide contraseña, no la escribas en la grabación: cancela y
explica que en la demo se usa un entorno aislado.

### 4. Buscar (0:45–0:55)

```text
1          -> Paquetes
f          -> buscar
"firefox"  -> escribir
Enter
Esc        -> volver al menú
```

Muestra cómo la lista se filtra mientras se escribe y cómo los atajos `i` y
`u` actúan sobre el elemento seleccionado.

### 5. Procesos (0:55–1:10)

```text
2      -> Procesos
s      -> ordenar por CPU
s      -> ordenar por memoria
f      -> filtrar por nombre
"python"
Enter
p      -> pausar la actualización
p      -> reanudar
Esc    -> volver al menú
```

Narra que la lista se actualiza cada 2 segundos y que `k` / `n` permiten
terminar y cambiar la prioridad. No termines procesos reales durante la
grabación.

### 6. Acerca de (1:10–1:25)

```text
8      -> Acerca de
?      -> ayuda de la pantalla
Esc    -> cerrar la ayuda
Esc    -> volver al menú
q      -> salir de TUI Manager
```

Enfoca el bloque de software y hardware estilo fastfetch. Recuerda revisar que
no se vea información sensible antes de publicar.

## Opción A: grabar con vhs

Guarda un fichero `demo.tape` (no incluido en el repo) con este contenido y
ejecútalo con `vhs demo.tape`. Ajusta los `Sleep` a tu equipo.

```text
Output demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 800
Set Theme "One Dark"
Set TypingSpeed 60ms
Set Padding 10

# 1. Arranque
Type "tui-manager --version"
Enter
Sleep 500ms
Type "tui-manager"
Enter
Sleep 2s

# 2. Menú con atajos
Type "?"
Sleep 1s
Escape
Sleep 500ms
Type "2"
Sleep 1s
Escape
Sleep 500ms
Type "0"
Sleep 1s
Escape
Sleep 500ms

# 3. Instalar paquete (entorno desechable)
Type "1"
Sleep 1s
Type "f"
Sleep 500ms
Type "htop"
Sleep 1s
Enter
Sleep 500ms
Type "u"
Sleep 1s
Escape
Sleep 500ms
Type "i"
Sleep 1s
Type "y"
Sleep 2s
Escape
Sleep 500ms

# 4. Buscar
Type "1"
Sleep 500ms
Type "f"
Type "firefox"
Sleep 1s
Enter
Sleep 1s
Escape
Sleep 500ms

# 5. Procesos
Type "2"
Sleep 1s
Type "s"
Sleep 500ms
Type "s"
Sleep 500ms
Type "f"
Type "python"
Sleep 1s
Enter
Sleep 1s
Type "p"
Sleep 500ms
Type "p"
Sleep 500ms
Escape
Sleep 500ms

# 6. Acerca de y salida
Type "8"
Sleep 2s
Type "?"
Sleep 1s
Escape
Sleep 500ms
Escape
Sleep 500ms
Type "q"
Sleep 1s
```

Para obtener un cast reproducible en vez de un GIF, cambia la primera línea
por `Output demo.cast`.

## Opción B: grabar con asciinema

```bash
asciinema rec demo.cast --title "TUI Manager 1.1.0 - demo"
```

Dentro de la sesión grabada, sigue la secuencia «Secuencias» de arriba, escribe
los comandos con normalidad y termina con `Ctrl+D`. Para revisar el resultado
sin enviarlo a ningún sitio:

```bash
asciinema play demo.cast
```

Si quieres convertir el cast a GIF, usa una herramienta local como
`agg` (por ejemplo `agg demo.cast demo.gif`). Cualquier subida a un servidor es
un paso manual y requiere autorización explícita.

## Checklist antes de compartir

- [ ] `tui-manager --version` muestra `1.1.0`.
- [ ] No aparecen contraseñas, tokens, correos ni nombres de host sensibles.
- [ ] No se han instalado ni terminado paquetes/procesos reales fuera de la VM.
- [ ] La grabación dura menos de 90 segundos y se entiende sin audio.
- [ ] Se ha revisado el GIF o el cast con `asciinema play` / visor local.
- [ ] Se ha decidido de forma explícita si la grabación se publica o no.
