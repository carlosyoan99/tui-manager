# Esqueleto de port FreeBSD para TUI Manager.
# Version 0.5.0 = release 0.5.0-beta.1 (PEP 440: 0.5.0b1).
# Antes de construir: verificar que el tag v${DISTVERSION} existe y generar
# distinfo con `make makesum`. No se ejecutó ningún build.

PORTNAME=	tui-manager
DISTVERSION=	0.5.0
CATEGORIES=	sysutils
MAINTAINER=	carlosyoan@local
COMMENT=	Portable terminal control panel for packages and processes

LICENSE=	MIT

USE_GITHUB=	yes
GH_ACCOUNT=	carlosyoan
GH_PROJECT=	TUI-Manager
GH_TAGNAME=	v${DISTVERSION}

USE_PYTHON=	autoplist distutils
NO_ARCH=	yes

# requirements.txt: textual, pyyaml, python-json-logger.
# El port resuelve los ports de Python equivalentes; no se usan bindings nativos.
RUN_DEPENDS=	${PYTHON_PKGNAMEPREFIX}textual>=0.40.0:devel/py-textual@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}yaml>=6.0.1:devel/py-yaml@${PY_FLAVOR} \
		${PYTHON_PKGNAMEPREFIX}json-logger>=2.0.7:devel/py-json-logger@${PY_FLAVOR}

.include <bsd.port.mk>
