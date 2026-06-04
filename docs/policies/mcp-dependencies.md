# MCP Dependency Policy

Cada MCP de dominio debe declarar solo las dependencias necesarias para ese dominio.

## Reglas

- El paquete base `forgetools` no debe instalar dependencias opcionales de dominios especificos.
- El extra raiz `.[mcp]` debe contener solo runtime compartido para servidores MCP.
- Dependencias de proveedores externos deben vivir en `mcps/<dominio>/pyproject.toml`.
- Si un dominio usa una dependencia opcional, su target `make install-mcp-<dominio>` debe instalarla.
- No usar `--no-deps` al instalar paquetes de dominio, salvo que el dominio declare explicitamente `dependencies = []` y exista una razon documentada.

## Estado actual

- Runtime comun MCP: `fastmcp`.
- Web search: `ddgs`, declarado solo en `mcps/websearch/pyproject.toml`.
- Los demas dominios usan dependencias del paquete base o herramientas CLI externas.

## Criterio de aceptacion

Cuando se agregue una tool nueva:

- Si usa solo stdlib o CLI externa, no agregar dependencia Python.
- Si usa libreria Python, agregarla al `pyproject.toml` del dominio correspondiente.
- Si la dependencia es compartida por varios dominios, justificar si debe ir al extra raiz `.[mcp]`.
