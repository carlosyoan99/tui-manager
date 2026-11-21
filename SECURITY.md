# Política de seguridad

TUI Manager se ejecuta en el equipo del usuario y se comunica con gestores de
paquetes, procesos y archivos de configuración del sistema. Tomamos en serio
los informes de seguridad y agradecemos cualquier reporte responsable.

Repositorio oficial: [carlosyoan99/tui-manager](https://github.com/carlosyoan99/tui-manager).

## Versiones con soporte

| Versión | Estado |
|---|---|
| `1.1.0` | Versión publicada actual; recibe correcciones de seguridad |
| `1.2.0` | En desarrollo; los arreglos se aplican también aquí cuando aplica |
| Anteriores | Sin soporte: actualiza a `1.1.0` o superior |

## Cómo reportar una vulnerabilidad

**No abras un issue público** ni comentes el problema en discusiones, PRs o
redes sociales hasta que exista una corrección. **GitHub es el único canal
oficial** para reportes de seguridad: abre un **GitHub Security Advisory
(privado)** en
https://github.com/carlosyoan99/tui-manager/security/advisories/new
(también disponible en la pestaña *Security* → *Report a vulnerability*).
El borrador es privado entre tú y el maintainer. No se aceptan reportes por
correo electrónico.

Si no estás seguro de que sea una vulnerabilidad, reporta igual por ese mismo
canal privado: prefiero revisar un falso positivo a perder un aviso real.

Para bugs y preguntas que **no** sean de seguridad, usa
[GitHub Issues](https://github.com/carlosyoan99/tui-manager/issues) o
[GitHub Discussions](https://github.com/carlosyoan99/tui-manager/discussions).

## Qué incluir en el informe

Cuanta más información, más rápido se puede reproducir:

- Descripción del problema y tipo de impacto (ejecución de comandos, escalada
  de permisos, lectura/escritura de archivos, denegación de servicio, etc.).
- Versión afectada (`tui-manager --version`) y sistema: Linux/BSD/Termux,
  distro, gestor de ventanas o escritorio.
- Salida de `tui-manager --doctor`.
- Pasos mínimos para reproducir y, si puedes, una prueba de concepto. No
  adjuntes datos personales ni credenciales reales.
- Una idea de mitigación o alcance que hayas identificado, si la tienes.

## Qué esperar

- Acuso recibo en un plazo de **5 días hábiles** y hago una primera evaluación
  en **10 días hábiles**. No es un SLA contractual: el proyecto es mantenido
  por una persona y puede haber retrasos; avisaré si es así.
- Si el informe se confirma, preparo una corrección, una versión nueva y un
  aviso público coordinado contigo.
- Te daré crédito en el aviso si lo deseas; también puedes pedir anonimato.
- Te avisaré cuando el arreglo esté disponible para que puedas verificarlo
  antes de la divulgación pública.

## Alcance y superficie relevante

Agradezco especialmente reportes sobre:

- Inyección de comandos o argumentos en los adaptadores de paquetes/entorno.
- Uso indebido de `sudo`/`doas` o elevación de privilegios inesperada.
- Manejo inseguro de rutas de configuración (`~/.config/tui-manager`) o de
  copias de seguridad de archivos del WM/DE.
- Escapes de marcado de textual, falsificación de la salida `--doctor` o
  espionaje de información del sistema en `Acerca de`.
- Dependencias con vulnerabilidades conocidas en `requirements.txt`.

El comando `--doctor` invoca únicamente el flag `--version` de una lista fija
de ejecutables y tiene prohibido ejecutar otra cosa; cualquier forma de sortear
esa restricción se considera un hallazgo de seguridad.

## Divulgación responsable

Mantén la confidencialidad mientras se prepara la corrección. Una vez
publicada la versión con el arreglo, puedes divulgar tu hallazgo. TUI Manager
se distribuye bajo licencia [MIT](https://opensource.org/licenses/MIT), sin
garantía de ningún tipo; esta política describe buenas prácticas, no un
contrato.
