# Guía de Uso

## Introducción

TUI Manager es una aplicación de interfaz de usuario terminal para gestionar paquetes y monitorear procesos en Linux. Esta guía te enseñará a usar todas las funcionalidades principales.

## Inicio de la Aplicación

### Ejecutar la Aplicación

```bash
python main.py
```

### Primera Vez

Al ejecutar por primera vez, el programa:
1. Detectará tu distribución Linux
2. Cargará los módulos de paquetes y procesos
3. Mostrará el menú principal

## Navegación

### Atajos de Teclado

| Tecla | Acción |
|-------|--------|
| `↑` / `↓` | Navegar entre elementos |
| `Enter` | Seleccionar elemento |
| `Esc` | Volver atrás / Cerrar |
| `?` | Mostrar ayuda |
| `q` | Salir del programa |
| `s` | Cambiar tema |
| `r` | Refrescar datos |

### Navegación en Menús

1. Usa las flechas `↑` y `↓` para seleccionar opciones
2. Presiona `Enter` para entrar en un submenú
3. Usa `Esc` para volver al menú anterior
4. Presiona `q` para salir del programa

## Gestión de Paquetes

### Ver Paquetes Instalados

1. Ve al menú principal
2. Selecciona "Gestión de Paquetes" y presiona `Enter`
3. Verás una lista de todos los paquetes instalados

#### Filtros

- **Por nombre**: Escribe en el campo de búsqueda para filtrar por nombre
- **Por categoría**: Usa los botones de filtro para ver solo ciertas categorías
- **Por estado**: Ver solo instalados o disponibles

### Buscar Paquetes

1. En la pantalla de gestión de paquetes
2. Escribe el nombre o parte del nombre en el campo de búsqueda
3. Presiona `Enter` o usa las flechas para navegar

### Instalar Paquetes

1. Busca el paquete que deseas instalar
2. Selecciona el paquete y presiona `Enter`
3. Verás los detalles del paquete
4. Presiona "Instalar" en el panel de detalles
5. Confirma la instalación si es necesario
6. Espera a que termine la instalación
7. El paquete aparecerá en la lista de instalados

### Desinstalar Paquetes

1. Ve a la lista de paquetes instalados
2. Selecciona el paquete que deseas desinstalar
3. Presiona `Enter` para ver los detalles
4. Presiona "Desinstalar"
5. Confirma la desinstalación si es necesario
6. El paquete será eliminado

### Ver Detalles de un Paquete

1. Selecciona un paquete en la lista
2. Presiona `Enter`
3. Verás información detallada:
   - Nombre
   - Versión
   - Descripción
   - Dependencias
   - Tamaño
   - Categoría

### Actualizar Repositorios

1. En el menú de gestión de paquetes
2. Presiona `F5` o selecciona "Actualizar Repositorios"
3. Espera a que termine la actualización

### Actualizar Sistema

1. En el menú de gestión de paquetes
2. Presiona `F6` o selecciona "Actualizar Sistema"
3. Selecciona los paquetes a actualizar
4. Confirma la actualización

## Monitoreo de Procesos

### Ver Procesos

1. Ve al menú principal
2. Selecciona "Monitoreo de Procesos" y presiona `Enter`
3. Verás una lista de todos los procesos en ejecución

### Filtros de Procesos

#### Por Usuario
- Usa el campo de filtro de usuario
- Por ejemplo: `carlosyoan` para ver solo tus procesos

#### Por Nombre
- Usa el campo de filtro de nombre
- Por ejemplo: `firefox` para ver solo procesos de Firefox

#### Por CPU
- Usa el filtro de CPU mínimo/máximo
- Por ejemplo: `> 5%` para ver solo procesos que usan más del 5% de CPU

#### Por Memoria
- Usa el filtro de memoria mínimo/máximo
- Por ejemplo: `> 100 MB` para ver solo procesos que usan más de 100 MB

### Ver Detalles de un Proceso

1. Selecciona un proceso en la lista
2. Presiona `Enter` para ver los detalles
3. Verás información detallada:
   - PID (Process ID)
   - Usuario
   - CPU usage (%)
   - Memory usage (%)
   - Virtual Memory (KB)
   - Resident Memory (KB)
   - Prioridad (Nice)
   - Tiempo de ejecución
   - Comando completo

### Terminar un Proceso

1. Selecciona un proceso en la lista
2. Presiona `Enter` para ver los detalles
3. Presiona "Terminar" o usa la tecla `K`
4. El sistema te pedirá confirmación
5. Confirma para terminar el proceso

### Cambiar Prioridad

1. Selecciona un proceso en la lista
2. Presiona `Enter` para ver los detalles
3. Presiona "Prioridad" o usa la tecla `N`
4. Selecciona la nueva prioridad:
   - `-20` (máxima prioridad, proceso importante)
   - `-10` (alta prioridad)
   - `0` (prioridad normal)
   - `10` (baja prioridad)
   - `19` (mínima prioridad)

### Actualizar en Tiempo Real

Los procesos se actualizan automáticamente cada 2 segundos.
Puedes forzar una actualización presionando `F5` o `R`.

## Configuración

### Cambiar Tema

1. En el menú principal
2. Ve a "Configuración"
3. Selecciona "Temas"
4. Usa las flechas para navegar entre temas
5. Presiona `Enter` para seleccionar un tema
6. Los temas disponibles:
   - Dark (oscuro por defecto)
   - Light (claro)
   - Retro (retro)

### Configuración de Actualización

En la configuración puedes ajustar:
- **Auto-update**: Actualizar repositorios automáticamente al iniciar
- **Refresh interval**: Intervalo de actualización de procesos (segundos)
- **Show details**: Mostrar detalles adicionales en la lista

### Guardar Configuración

La configuración se guarda automáticamente después de cada cambio.

## Ayuda

### Mostrar Ayuda

Presiona `?` en cualquier pantalla para ver la ayuda específica de esa pantalla.

### Información del Sistema

1. Ve al menú principal
2. Selecciona "Acerca de"
3. Verás información sobre:
   - Versión del programa
   - Distribución Linux detectada
   - Versión de Python
   - Información de licencia

## Ejemplos de Uso

### Ejemplo 1: Instalar Firefox

1. Ve a "Gestión de Paquetes"
2. En el campo de búsqueda escribe "firefox"
3. Selecciona "firefox" de la lista
4. Presiona `Enter` para ver detalles
5. Presiona "Instalar"
6. Espera a que termine la instalación
7. Firefox aparecerá en la lista de instalados

### Ejemplo 2: Terminar un Proceso Lento

1. Ve a "Monitoreo de Procesos"
2. Usa el filtro de CPU: `> 10%`
3. Selecciona el proceso que usa más CPU
4. Presiona `Enter` para ver detalles
5. Presiona "Terminar"
6. Confirma la acción

### Ejemplo 3: Buscar Paquetes por Categoría

1. Ve a "Gestión de Paquetes"
2. Presiona `F3` o selecciona "Filtros"
3. Selecciona "Desarrollo"
4. Verás solo los paquetes de desarrollo
5. Presiona `F3` o selecciona "General" para ver todos

## Solución de Problemas

### No puedo instalar paquetes

- Verifica que tienes permisos de administrador
- Ejecuta el programa con sudo si es necesario
- Verifica que los repositorios están actualizados

### Los procesos no se actualizan

- Presiona `R` o `F5` para forzar una actualización
- Verifica que el comando `ps` funciona en tu terminal
- Revisa los logs en `~/.tui-manager/logs/`

### La aplicación no se inicia

- Verifica que tienes Python 3.10 o superior instalado
- Ejecuta `python main.py` en la terminal para ver errores específicos
- Revisa los logs en `~/.tui-manager/logs/`

## Atajos Rápidos

### En la pantalla de Gestión de Paquetes

| Tecla | Acción |
|-------|--------|
| `F1` | Ayuda |
| `F2` | Buscar |
| `F3` | Filtros |
| `F4` | Ordenar |
| `F5` | Actualizar |
| `F6` | Sistema completo |
| `s` | Cambiar tema |
| `q` | Salir |

### En la pantalla de Monitoreo de Procesos

| Tecla | Acción |
|-------|--------|
| `F1` | Ayuda |
| `F2` | Filtrar |
| `F5` | Actualizar |
| `R` | Refrescar |
| `K` | Terminar proceso |
| `N` | Cambiar prioridad |
| `s` | Cambiar tema |
| `q` | Salir |

## Consejos Pro

1. **Usa los filtros**: Los filtros pueden ahorrarte mucho tiempo
2. **Ordena por CPU/Memoria**: Útil para encontrar procesos problemáticos
3. **Usa temas claros**: Mejor visibilidad en pantallas de alta resolución
4. **Actualiza regularmente**: Mantén tus paquetes y repositorios al día
5. **Usa atajos**: Los atajos de teclado hacen la navegación más rápida

## Siguiente Paso

- Lee la [Documentación de la API](API.md) para detalles técnicos
- Consulta la [Especificación Técnica](TECHNICAL_SPECS.md) para entender la arquitectura
- Contribuye al proyecto en [GitHub](https://github.com/tu-usuario/TUI-Manager)
