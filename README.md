# Portal de entornos

Web estática (GitHub Pages) con el inventario de **cuentas AWS** y **clusters OpenShift**
por entorno (`dev`, `pre`, `pro`). Los datos viven en un único fichero YAML; en cada push a
`main` se validan y se publica la web.

## Estructura

```
data/entornos.yaml           # inventario (lo único que hay que editar normalmente)
scripts/build.py             # valida el YAML y genera _site/
index.html                   # la web (HTML + CSS + JS, sin dependencias externas)
.github/workflows/pages.yml  # build + despliegue en GitHub Pages
```

## Añadir o editar un entorno

Añade una entrada a `data/entornos.yaml`:

```yaml
- nombre: Mi App - Preproducción      # obligatorio, único
  entorno: pre                        # obligatorio: dev | pre | pro
  tipo: openshift                     # obligatorio: aws | openshift
  aplicacion: mi-app
  cluster: ocp-pre-01
  api: https://api.ocp-pre-01.ejemplo.local:6443
  consola: https://console-openshift-console.apps.ocp-pre-01.ejemplo.local
  argocd: https://argocd.apps.ocp-pre-01.ejemplo.local
  namespaces: [mi-app-pre]
  confluence: https://ejemplo.atlassian.net/wiki/...
  notas: Texto libre.
  tags: [backend, java]
  equipo: plataforma                  # campo extra: se muestra y se busca igual
```

| Campo        | Tipo   | Notas                                              |
|--------------|--------|----------------------------------------------------|
| `nombre`     | texto  | **Obligatorio**. No puede repetirse.               |
| `entorno`    | texto  | **Obligatorio**. `dev`, `pre` o `pro`.             |
| `tipo`       | texto  | **Obligatorio**. `aws` u `openshift`.              |
| `aplicacion` | texto  | Se usa en el filtro de aplicación.                 |
| `cuenta_aws` | texto  | 12 dígitos **entre comillas** (`"012345678901"`).  |
| `region`, `cluster`, `notas` | texto |                                        |
| `api`, `consola`, `argocd`, `confluence` | URL | Deben empezar por `http(s)://`. |
| `namespaces`, `tags` | lista |                                              |
| *(otros)*    | libre  | Se muestran en la tarjeta y entran en la búsqueda. |

### Nada de secretos

El build **falla** si detecta algo que parezca un secreto:

- campos cuyo nombre contenga `password`, `passwd`, `contraseña`, `pwd`, `secret`, `token`,
  `apikey`/`api_key`, `private_key` o `credential`;
- valores con esas palabras seguidas de `:` / `=` (p. ej. `token=abc`);
- claves de acceso AWS (`AKIA…` / `ASIA…`) o claves privadas PEM.

Este repositorio y la web son solo para **datos de referencia** (IDs, URLs, nombres).
Las credenciales van en el gestor de secretos correspondiente.

## Probar en local

```bash
pip install pyyaml
python scripts/build.py              # valida y genera _site/
python -m http.server 8000 -d _site  # abre http://localhost:8000
```

> `index.html` carga `data.json` con `fetch`, así que hay que servirlo por HTTP
> (abrirlo con doble clic, `file://`, no funciona).

## Uso de la web

- **Buscador**: busca en todos los campos (incluidos los extra). Varias palabras = todas
  deben aparecer. Ignora mayúsculas y tildes y resalta las coincidencias.
- La búsqueda y los filtros se guardan en la URL (`?q=pagos&entorno=pro`), así que se
  pueden compartir enlaces.
- Atajos: `/` enfoca el buscador, `Esc` lo limpia.
- Filtros por entorno, tipo y aplicación. Clic en un tag para buscarlo.
- Botón **copiar** en cuenta AWS, cluster y API.
- Modo oscuro automático (según el sistema) o con el botón 🌓 (se recuerda en el navegador).

## Despliegue

El workflow `.github/workflows/pages.yml` se ejecuta en cada push a `main` (y manualmente
desde *Actions*): instala `pyyaml`, ejecuta `scripts/build.py` y publica `_site/` con
`actions/upload-pages-artifact` y `actions/deploy-pages`.

**Configuración única**: en *Settings → Pages → Build and deployment → Source* elige
**GitHub Actions**.
