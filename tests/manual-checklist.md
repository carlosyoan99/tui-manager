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
