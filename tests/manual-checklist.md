# Checklist de sesión guiada (Beta 1)

Recorrido manual por las **10 pantallas** del menú principal. Marcá cada paso con
`[x]` cuando pase y dejá `[ ]` si falla (anotá el detalle debajo del ítem).

**Atajos del menú:** `[1]` Aplicaciones · `[2]` Procesos · `[3]` Sistema · `[4]` Temas ·
`[5]` Actualizar · `[6]` Ajustes · `[7]` Ayuda · `[8]` Acerca de · `[9]` Logs ·
`[0]` Catálogo de apps.

## Criterios que se verifican en CADA pantalla

- [ ] La pantalla abre con su atajo y **responde en <500 ms** (sin bloqueos visibles).
- [ ] **No aparece traceback** en pantalla ni en la salida de la terminal.
- [ ] Toda **acción destructiva pide confirmación** y no se ejecuta sin el OK explícito
      (en pantallas sin acciones destructivas, marcar el ítem "no aplica").
- [ ] Ante un fallo se muestra un **mensaje accionable**, nunca un error crudo.

**Precondición:** suite automatizada en verde (**158 tests**).

---

### [1] Aplicaciones

- [ ] Abrir con `[1]`: se muestra la lista de paquetes en <500 ms, sin traceback.
- [ ] Buscar un paquete y abrir su detalle: resultado esperado = información del
      paquete visible, sin traceback.
- [ ] Instalar/desinstalar un paquete: **pide confirmación**; al cancelar no se
      ejecuta ningún cambio.
- [ ] Al confirmar una desinstalación, la operación se completa y el paquete
      desaparece de la lista de instalados; si falla, se muestra mensaje accionable.

### [2] Procesos

- [ ] Abrir con `[2]`: listado de procesos en <500 ms, sin traceback.
- [ ] Aplicar un filtro (usuario/nombre/CPU/memoria): resultado esperado = lista
      filtrada sin traceback.
- [ ] Terminar un proceso: **pide confirmación**; al cancelar el proceso sigue vivo.
- [ ] Cambiar prioridad: se aplica el cambio y se refleja en el detalle, sin traceback.

### [3] Sistema

- [ ] Abrir con `[3]`: información del sistema en <500 ms, sin traceback.
- [ ] Revisar los datos mostrados: resultan completos y legibles, sin traceback.
- [ ] Sin acciones destructivas en esta pantalla: **confirmación no aplica**.

### [4] Temas

- [ ] Abrir con `[4]`: selector de temas en <500 ms, sin traceback.
- [ ] Cambiar de tema: el cambio se aplica y persiste al reabrir, sin traceback.
- [ ] Sin acciones destructivas en esta pantalla: **confirmación no aplica**.

### [5] Actualizar

- [ ] Abrir con `[5]`: opciones de actualización en <500 ms, sin traceback.
- [ ] Actualizar repositorios / actualizar el sistema: **pide confirmación** antes
      de ejecutar; al cancelar no se realiza ninguna actualización.
- [ ] Al confirmar, la operación se ejecuta y se muestra el resultado; si falla,
      se muestra mensaje accionable y no traceback.

### [6] Ajustes

- [ ] Abrir con `[6]`: panel de ajustes en <500 ms, sin traceback.
- [ ] Modificar un ajuste y guardar: el valor persiste al reabrir, sin traceback.
- [ ] Sin acciones destructivas en esta pantalla: **confirmación no aplica**.

### [7] Ayuda

- [ ] Abrir con `[7]`: ayuda general en <500 ms, sin traceback.
- [ ] Presionar `?`: se muestra la **ayuda contextual** de la pantalla actual,
      sin traceback.
- [ ] Sin acciones destructivas en esta pantalla: **confirmación no aplica**.

### [8] Acerca de

- [ ] Abrir con `[8]`: se muestra versión **0.3.0-alpha.3** y datos de distribución,
      Python y licencia en <500 ms, sin traceback.
- [ ] Sin acciones destructivas en esta pantalla: **confirmación no aplica**.

### [9] Logs

- [ ] Abrir con `[9]`: se muestran los registros en <500 ms, sin traceback.
- [ ] Los eventos de instalación/rollback aparecen registrados y son legibles;
      sin traceback.
- [ ] Sin acciones destructivas en esta pantalla: **confirmación no aplica**.

### [0] Catálogo de apps

- [ ] Abrir con `[0]`: catálogo en <500 ms, sin traceback.
- [ ] El catálogo muestra **179 aplicaciones en 29 categorías**; sin traceback.
- [ ] Los AppImage listados son **4** y todos tienen **URL verificada** (HTTP 200).
- [ ] Elegir una app con fuente externa / no oficial: **pide confirmación**; al
      cancelar no se instala nada.
- [ ] Instalar una app: resultado esperado = mensaje con `ok`, `source`,
      `returncode`, `actions` y `error`; si falla, mensaje accionable y no traceback.
- [ ] Verificar el rollback tras un fallo: **nunca borra archivos del usuario**;
      solo revierte directorios vacíos creados por el propio comando.

---

## Resultado de la sesión

- [ ] Las 10 pantallas pasaron los criterios globales (<500 ms, sin traceback,
      confirmación en acciones destructivas).
- [ ] No quedan ítems sin marcar ni incidencias anotadas.

---

## MEDICIÓN (Beta 3) — rendimiento y estabilidad

Se ejecuta al cerrar Beta 3, en hardware modesto (≤ 8 GB RAM). Anotá el valor
real medido en cada casilla; el umbral es **arranque < 2 s**, **refresco
< 500 ms**, **5000 paquetes navegables** y **ningún bloqueo de la UI > 500 ms**.

### Cómo medirlo

```bash
# 1) Arranque en frío: tiempo hasta imprimir la versión (proceso completo,
#    sin llegar a lanzar la TUI). Repetir 3 veces y anotar el peor caso.
time .venv/bin/python -m tui_manager.main --version

# 2) Refresco, 5000 paquetes y ausencia de bloqueo: test automatizado de
#    regresión de rendimiento (tests/test_perf.py, entregado en B3-1).
#    Usa time.perf_counter() y fakes: sin subprocess reales ni tiempo real
#    contra comandos del sistema.
.venv/bin/python -m pytest -q tests/test_perf.py
```

- [ ] **Arranque < 2 s:** `time .venv/bin/python -m tui_manager.main --version`
      tarda menos de 2 s (peor caso de 3 repeticiones: ______ s).
- [ ] **Refresco < 500 ms:** el peor tiempo de refresco medido por el test de
      rendimiento está por debajo de 500 ms (peor caso: ______ ms).
- [ ] **5000 paquetes:** la lista de 5000 paquetes simulados se navega con
      paginación y respuesta inmediata, sin bloqueo perceptible
      (peor caso: ______ ms).
- [ ] **Sin bloqueo > 500 ms:** ninguna llamada/subprocess bloquea el hilo de
      la UI más de 500 ms; verificado por los tests de rendimiento y de
      procesos en segundo plano (B3-1 / B3-2).
- [ ] Repetidas las mediciones al menos 3 veces y anotado el **peor caso** en
      cada casilla (no solo la media).
- [ ] Suite automatizada completa en verde (**236 tests**) antes y después de
      medir: `.venv/bin/python -m pytest -q`.
