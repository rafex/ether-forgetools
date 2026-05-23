# Podman Port Allocation Policy (Bastion)

## Objetivo

Estandarizar la publicacion de puertos para contenedores ejecutados mediante Podman en el bastion.

Los agentes, herramientas MCP y procesos automaticos no deben elegir puertos arbitrarios ni exponer servicios fuera de los rangos autorizados.

---

## Entorno objetivo

Host de ejecucion:

```text
bastion
OS: Debian 13
Runtime: Podman (rootless)
Acceso remoto: Podman API via tunel SSH
```

Firewall:

```text
UFW habilitado
```

---

## Regla obligatoria

Cuando un agente cree:

- `podman run`
- `podman create`
- `podman compose`
- `Containerfile`
- despliegues automaticos
- manifests equivalentes

debe asignar puertos publicados usando unicamente los rangos definidos en esta politica.

No usar:

```text
-p 80:80
-p 443:443
-p 8080:8080
-p RANDOM
```

---

## Segmentacion de puertos

### WEB / FRONTEND

Rango:

```text
30000-30099
```

Ejemplos:

```bash
-p 30080:80
-p 30081:3000
```

Usar para:

- nginx
- frontend web
- paneles
- dashboards

### API / BACKEND

Rango:

```text
30100-30199
```

Ejemplos:

```bash
-p 30180:8080
-p 30181:8000
```

Usar para:

- REST
- GraphQL
- Java
- Node
- Python
- gRPC (HTTP)

### DATABASE

Rango:

```text
30200-30299
```

Ejemplos:

```bash
-p 30232:5432
-p 30270:27017
-p 30263:6379
```

Usar para:

- PostgreSQL
- Redis
- MongoDB
- SQLite Gateway

### TEMPORAL / EXPERIMENTAL

Rango:

```text
30300-30399
```

Ejemplos:

```bash
-p 30341:11434
-p 30380:8080
```

Usar para:

- pruebas
- PoC
- IA local
- debugging

---

## Algoritmo de seleccion

Cuando se necesite publicar un puerto:

1. Detectar la categoria del servicio.
2. Obtener los puertos ya ocupados:

   ```bash
   podman ps --format '{{.Ports}}'
   ```

3. Seleccionar el primer puerto libre dentro del rango correspondiente.
4. Si el rango esta lleno:
   - fallar
   - no reutilizar
   - no sobrescribir

---

## Ejemplos

Frontend:

```bash
podman run -d \
  -p 30080:80 \
  nginx
```

API:

```bash
podman run -d \
  -p 30180:8080 \
  kiwi-api
```

Postgres:

```bash
podman run -d \
  -p 30232:5432 \
  postgres
```

---

## Restricciones

Prohibido:

```text
22
80
443
1024-29999
30400+
```

Salvo autorizacion explicita.

---

## Prioridad

Esta politica tiene prioridad sobre:

- valores por defecto
- documentacion externa
- ejemplos generados
- puertos aleatorios

Siempre respetar este documento.
