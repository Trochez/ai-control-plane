# Documentación completa de ai-loop v4.2

**Proyecto:** `agentic_pipeline / ai-loop`  
**Versión documentada:** `4.2.0`  
**Proyecto ChatGPT objetivo:** `bot_trading`  
**Repositorio objetivo:** `Trochez/bot_trading`  
**Rama objetivo:** `feature/GRU`  
**Control plane local:** `/mnt/d/works/ai-control-plane`  
**Runtime instalado:** `/opt/ai-loop`  
**Estado, logs y evidencias:** `/var/lib/ai-loop`  

---

# 1. Qué es ai-loop

`ai-loop` es un **controlador autónomo de implementación, validación y recuperación de fallos** que conecta varias piezas:

- ChatGPT Web dentro del proyecto `bot_trading`;
- GPT-5.6 Sol en modo normal **Chat**, con razonamiento **High**;
- un controlador determinista en Python;
- un navegador Chrome controlado por Playwright;
- OpenCode como capa de interpretación semántica;
- el repositorio Git/GitHub de `Trochez/bot_trading`;
- comandos locales de validación;
- un VPS accesible mediante un wrapper controlado;
- Semaphore/CI;
- archivos de plan `.md`;
- evidencias, estados, hashes y logs persistentes.

Su objetivo no es simplemente “abrir ChatGPT y enviar un prompt”. Su objetivo real es completar un ciclo parecido a este:

```text
PLAN .md
   ↓
crear chat nuevo dentro de bot_trading
   ↓
Chat + GPT-5.6 Sol + High
   ↓
adjuntar plan
   ↓
enviar instrucción de implementación
   ↓
esperar respuesta de ChatGPT
   ↓
interpretar qué necesita hacer el operator
   ↓
ejecutar comandos permitidos
   ↓
devolver evidencia literal al mismo chat
   ↓
detectar commit/candidato nuevo en GitHub
   ↓
esperar CI
   ↓
si CI pasa → revisión final → GO
   ↓
si CI falla → recolectar evidencia → diagnóstico → nuevo plan
   ↓
descargar el nuevo plan .md
   ↓
crear otro chat de implementación
   ↓
repetir
```

El loop finaliza únicamente cuando existe un candidato concreto, ese candidato coincide con la rama esperada, CI está exitoso y ChatGPT declara `GO`, que luego vuelve a ser validado por el controlador.

---

# 2. El problema que resuelve

Sin `ai-loop`, un flujo complejo de implementación suele requerir intervención humana repetitiva:

1. abrir ChatGPT;
2. adjuntar un plan;
3. pedir la implementación;
4. esperar;
5. revisar la respuesta;
6. ejecutar manualmente comandos que ChatGPT solicita;
7. copiar sus resultados;
8. esperar CI;
9. abrir Semaphore;
10. copiar logs de un fallo;
11. pedir diagnóstico;
12. pedir un nuevo plan;
13. descargar ese plan;
14. abrir otro chat;
15. repetir hasta que todo quede verde.

`ai-loop` automatiza ese ciclo, pero intenta hacerlo con una propiedad importante:

> Las decisiones semánticas pueden provenir de IA, pero las acciones físicas importantes y las transiciones de estado deben ser comprobadas por código determinista.

Esa separación es el principio central del proyecto.

---

# 3. Idea fundamental: autoridad semántica vs. autoridad física

El sistema separa dos tipos de autoridad.

## 3.1 Autoridad semántica

La IA puede interpretar frases como:

- “necesito ejecutar estos comandos”;
- “el diagnóstico está listo”;
- “debo continuar”;
- “el plan de remediación está listo”;
- “la implementación está completa”;
- “GO”.

Esto requiere lenguaje natural y contexto, por lo que OpenCode se usa como intérprete semántico.

## 3.2 Autoridad física

El controlador nunca debe considerar cierta una acción únicamente porque un modelo la afirmó.

Ejemplos:

- que un archivo exista;
- que un archivo adjunto sea el correcto;
- que una orden se haya enviado;
- que el proyecto seleccionado sea `bot_trading`;
- que el modelo realmente sea GPT-5.6 Sol;
- que el reasoning realmente sea High;
- que un bloque de shell tenga determinados bytes;
- que GitHub esté en cierto SHA;
- que Semaphore esté ejecutando el SHA correcto;
- que CI haya terminado exitosamente;
- que una orden ya se haya ejecutado.

Todo eso debe comprobarse mediante estado observable, hashes, APIs, filesystem, DOM o herramientas deterministas.

---

# 4. Arquitectura de alto nivel

La arquitectura actual se puede visualizar así:

```text
┌───────────────────────────────────────────────────────┐
│                  ai-loop controller                   │
│               /opt/ai-loop/ai-loopd-v3.py            │
│                  versión lógica 4.2.0                 │
└───────────────┬───────────────────┬───────────────────┘
                │                   │
                │ JSONL/RPC         │ texto/razonamiento
                ▼                   ▼
┌──────────────────────────┐   ┌────────────────────────┐
│ Browser Transport Broker │   │       OpenCode         │
│ browser-broker-v1.cjs    │   │ clasificación semántica│
│                          │   │ sin autoridad browser  │
│ Único dueño del perfil   │   └────────────────────────┘
│ Chrome de ChatGPT        │
└───────────────┬──────────┘
                │ Playwright
                ▼
┌───────────────────────────────────────────────────────┐
│                     ChatGPT Web                       │
│ Project: bot_trading                                  │
│ Surface: Chat                                         │
│ Model: GPT-5.6 Sol                                    │
│ Reasoning: High                                       │
└───────────────────────────────────────────────────────┘

        ┌──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
     GitHub          Local           VPS          Semaphore
       gh             bash        vps-ssh          CI/web
```

---

# 5. Componentes principales

## 5.1 `ai-loopd-v3.py`

Aunque el archivo conserva el nombre histórico `ai-loopd-v3.py`, la versión lógica actual es:

```text
VERSION = 4.2.0
```

Es el cerebro determinista del sistema.

Responsabilidades:

- crear y cargar el estado de un run;
- impedir dos controllers simultáneos;
- iniciar y administrar el Browser Broker;
- crear el chat inicial;
- enviar mensajes;
- observar respuestas;
- pedir interpretación semántica a OpenCode;
- registrar acciones pendientes;
- ejecutar acciones permitidas;
- devolver resultados;
- detectar nuevos commits;
- vigilar CI;
- entrar en análisis de fallos;
- descargar planes;
- reiniciar la iteración;
- aceptar o rechazar un `GO`;
- persistir absolutamente todo lo relevante.

---

## 5.2 `browser-broker-v1.cjs`

Es un proceso Node.js/Playwright persistente.

Su función es ser **el único propietario del navegador ChatGPT durante el run**.

Esto evita que:

- OpenCode abra un Chrome;
- otro worker abra otro Chrome;
- dos procesos intenten usar el mismo perfil;
- la sesión autenticada se bloquee;
- el estado del browser se pierda entre cada operación.

El broker usa un perfil persistente, normalmente:

```text
~/.cache/ai-loop-chatgpt-profile
```

El controller se comunica con el broker por mensajes JSONL.

Ejemplo conceptual:

```json
{
  "request_id": "abc123",
  "operation": "ENSURE_CHAT_POLICY",
  "arguments": {
    "projectUrl": "...",
    "projectName": "bot_trading"
  }
}
```

El broker responde:

```json
{
  "request_id": "abc123",
  "status": "PASS",
  "evidence": {
    "chat": true,
    "model": true,
    "high": true
  }
}
```

---

# 6. Operaciones disponibles en el Browser Broker

El broker soporta las siguientes operaciones principales.

## `HEALTH`

Comprueba que el proceso está vivo.

Devuelve:

- `PASS`;
- `epoch`;
- URL actual.

El `epoch` identifica una instancia concreta del broker.

---

## `NAVIGATE_PROJECT`

Navega al proyecto objetivo y espera evidencia de que el contexto pertenece a ese proyecto.

---

## `NAVIGATE_URL`

Navega a una URL concreta.

---

## `OBSERVE_CONTEXT`

Lee el estado del DOM sin efectuar una acción.

Produce información como:

- URL;
- proyecto detectado;
- señales positivas del proyecto;
- señales negativas;
- composer visible;
- controles visibles;
- mensajes user/assistant;
- cantidad de turnos.

---

## `ENSURE_FRESH_PROJECT_DRAFT`

Garantiza que existe un draft vacío nuevo dentro del proyecto correcto.

Este paso es crítico porque entrar en la URL del proyecto puede restaurar un chat histórico.

v4.2 trata explícitamente este caso.

---

## `ENSURE_CHAT_POLICY`

Garantiza:

```text
surface = Chat
model = GPT-5.6 Sol
reasoning = High
```

Si encuentra Work/Codex u otro reasoning/model, intenta corregirlo sin enviar mensajes.

---

## `ATTACH_FILE`

Adjunta físicamente un archivo al composer actual.

Puede usar:

- `input[type=file].setInputFiles()`;
- un file chooser real cuando la UI exige abrir primero un menú.

---

## `FILL_COMPOSER`

Escribe el mensaje exacto en el composer y verifica que el contenido final coincide.

---

## `SEND_ATOMIC`

Es la única operación autorizada para hacer clic en Send dentro del broker.

Antes de enviar verifica el contexto y después comprueba que el marcador único apareció como turno del usuario.

---

## `OBSERVE_DELIVERY`

Busca un `delivery_id` previamente enviado.

Se utiliza para reconciliar estados ambiguos y evitar duplicados.

---

## `OBSERVE_RESPONSE`

Obtiene la última respuesta de Assistant y devuelve:

- estado de generación;
- id del mensaje;
- texto exacto;
- SHA-256 del texto;
- archivo local con ese texto;
- bloques de código detectados;
- SHA y tamaño de cada bloque.

---

## `MATERIALIZE_CODE_BLOCK`

Extrae del DOM el bloque de código seleccionado y lo escribe en un archivo local.

El caller debe indicar:

- índice del bloque;
- SHA esperado;
- tamaño esperado.

Si no coincide, la operación se rechaza.

---

## `DOWNLOAD_ARTIFACT`

Busca un artefacto descargable en la respuesta más reciente.

Soporta varios mecanismos:

- enlaces HTTP/HTTPS;
- `blob:`;
- `data:`;
- evento real de download.

El resultado final se escribe a disco y se devuelve con SHA-256.

---

## `SEMAPHORE_READONLY`

Abre Semaphore de forma read-only para obtener evidencia sobre:

- SHA;
- run id;
- pipeline id;
- estado;
- resultado.

Si la autenticación requiere una intervención que no puede automatizarse de forma segura, devuelve un bloqueo humano explícito.

---

## `CAPTURE_DIAGNOSTICS`

Genera evidencia diagnóstica del browser:

```text
.json
.html
.png
```

---

## `CLOSE`

Cierra el contexto persistente.

---

# 7. Cómo se identifica correctamente el proyecto `bot_trading`

Una de las lecciones más importantes de las versiones anteriores fue que:

```text
URL contiene g-p-...bot-trading
```

no puede ser la única prueba.

ChatGPT puede mostrar:

```text
https://chatgpt.com/
```

mientras el composer dice:

```text
New chat in Bot_trading
```

Por eso v4.2 calcula:

```text
projectContext = TARGET | OTHER | UNKNOWN
```

---

## 7.1 Señales positivas

Puede usar:

- URL contiene el `projectId`;
- existe un anchor cuyo `href` contiene el `projectId`;
- el proyecto objetivo está seleccionado;
- el composer dice `New chat in Bot_trading`;
- existe un header correspondiente al proyecto.

Ejemplos de señales internas:

```text
url_project_id
project_anchor_mapped
sidebar_target_link_present
selected_sidebar_project_id
project_scoped_composer
project_header
```

---

## 7.2 Señales negativas

Ejemplos:

- otro proyecto aparece seleccionado;
- el composer dice `New chat in <otro proyecto>`;
- hay evidencia positiva de un proyecto distinto.

---

## 7.3 Decisión

Conceptualmente:

```text
si hay una señal negativa fuerte:
    OTHER

si existe prueba suficiente del proyecto objetivo:
    TARGET

si no se puede demostrar:
    UNKNOWN
```

No se envía ningún mensaje cuando la identidad del proyecto es dudosa.

---

# 8. Qué significa un “fresh project draft”

Un chat nuevo válido requiere simultáneamente:

```text
projectContext == TARGET
user_turns == 0
assistant_turns == 0
composer visible
```

No basta con:

```text
turns == 0
```

porque podría ser el chat global.

Tampoco basta con estar dentro de una conversación histórica perteneciente a `bot_trading`.

---

# 9. Cómo v4.2 crea un chat nuevo

La lógica es:

## Paso A: comprobar si ya existe un draft válido

Si la página actual ya cumple:

```text
TARGET + 0 turns + composer
```

se usa directamente.

---

## Paso B: detectar chat histórico

Se considera histórico cuando:

- ya existen turnos; o
- la URL contiene `/c/`.

Aunque ese chat pertenezca al proyecto correcto, v4.2 **no lo reutiliza para un nuevo loop**.

---

## Paso C: volver a la raíz exacta del proyecto

El broker navega a:

```text
https://chatgpt.com/g/<project-id>-bot-trading
```

y vuelve a evaluar.

---

## Paso D: intentar controles seguros

Si todavía no existe un draft vacío, usa candidatos acotados:

1. un control explícito `New chat in Bot_trading`;
2. un control `Chat` dentro de la zona principal/header;
3. un control `New chat` que no sea un link histórico `/c/`.

Después de cada clic vuelve a comprobar:

```text
TARGET + 0 turns + composer
```

Si una acción escapa del proyecto, reingresa inmediatamente al proyecto antes de continuar.

---

# 10. Política obligatoria de ChatGPT

Cada mensaje autoritativo debe realizarse en:

```text
Surface: Chat
Model: GPT-5.6 Sol
Reasoning: High
```

No se aceptan:

```text
Work
Codex
Sol Light
Instant
Medium
modelo desconocido
reasoning desconocido
```

---

# 11. Verificación del modelo

El sistema no considera que un click exitoso sea suficiente.

Ejemplo incorrecto:

```text
click "GPT-5.6 Sol"
→ asumir seleccionado
```

Ejemplo correcto:

```text
click "GPT-5.6 Sol"
→ volver a leer controles
→ verificar selected / aria-selected / aria-checked / data-state
→ PASS
```

Lo mismo ocurre con `High`.

---

# 12. Adjuntar el plan

El plan `.md` se adjunta antes del Send.

La prueba del attachment debe estar asociada al composer activo.

Se acepta evidencia como:

- el `input[type=file]` contiene exactamente ese filename;
- aparece un chip/card del archivo en el composer;
- el estado determinista de upload confirma ese archivo.

No debe bastar con que el nombre aparezca en cualquier parte del body.

---

# 13. Mensaje inicial de implementación

El prompt instalado por defecto está en:

```text
/opt/ai-loop/prompts/implement.txt
```

Contenido:

```text
team pipeline: 1. implement completely attached .md plan 2. unique commit push in current branch (feature/GRU)
```

El controller añade además un identificador único:

```text
[AI_LOOP_DELIVERY id=<id>]
```

Ejemplo:

```text
[AI_LOOP_DELIVERY id=4bf...]
team pipeline: 1. implement completely attached .md plan 2. unique commit push in current branch (feature/GRU)
```

Ese marcador sirve para:

- demostrar el envío;
- detectar un envío previo;
- impedir duplicados;
- recuperar después de un crash.

---

# 14. Ledger de delivery

Cada envío importante tiene un ledger.

Estados típicos:

```text
READY
SENDING
SENT
AMBIGUOUS
```

Antes del click se registra que el envío va a realizarse.

Después se busca el marcador dentro de un turno de usuario.

Si aparece:

```text
SENT
```

Si el click pudo ocurrir pero no existe confirmación:

```text
AMBIGUOUS
```

En estado ambiguo el sistema **no vuelve a pulsar Send a ciegas**.

Primero intenta reconciliar.

---

# 15. Por qué la prevención de duplicados es tan importante

Un mensaje duplicado puede causar:

- dos implementaciones;
- dos commits;
- dos pushes;
- dos pipelines CI;
- dos ejecuciones remotas;
- evidencia contradictoria;
- pérdida del modelo mental del chat.

Por eso `delivery_id` y persistencia de estado son fundamentales.

---

# 16. OpenCode: qué hace y qué NO hace

En v4.2 OpenCode se usa principalmente como **intérprete semántico**.

Puede analizar el texto de ChatGPT y proponer:

```text
OPERATOR_ACTION_REQUESTED
EVIDENCE_REQUESTED
DIAGNOSIS_READY
PLAN_READY
PLAN_INLINE_ONLY
PLAN_ARTIFACT_MISSING
SELF_CONTINUE
FINAL_GO
HUMAN_BLOCKED
NO_CHANGE
```

Pero OpenCode **no es autoridad física**.

No debe:

- decidir por sí solo que un archivo fue descargado;
- inventar que un comando fue ejecutado;
- afirmar que CI pasó;
- decidir que cierto SHA es el correcto sin comprobación;
- hacer click en Send;
- ser dueño del browser ChatGPT;
- pasar bytes de comandos como autoridad.

---

# 17. Observación de respuestas

El Browser Broker llama a:

```text
OBSERVE_RESPONSE
```

y obtiene la última respuesta del Assistant.

Puede clasificar:

```text
NO_ASSISTANT
GENERATING
RATE_LIMIT
SETTLED
```

Además escribe el texto de la respuesta a:

```text
/var/lib/ai-loop/runs/<RUN_ID>/browser/responses/<message-id>.txt
```

y calcula:

```text
assistant_text_sha256
```

---

# 18. Clasificación semántica

Una vez que la respuesta está `SETTLED`, el texto se entrega a OpenCode.

OpenCode devuelve una propuesta semántica estructurada.

Eventos admitidos:

## `OPERATOR_ACTION_REQUESTED`

ChatGPT está solicitando comandos concretos al operator.

---

## `EVIDENCE_REQUESTED`

ChatGPT necesita evidencia adicional pero todavía no proporcionó los comandos exactos.

El controller puede responder pidiendo:

```text
Provide the exact command(s) required...
```

---

## `DIAGNOSIS_READY`

El diagnóstico posterior al fallo está completo.

---

## `PLAN_READY`

Existe un nuevo plan de implementación y debe existir como artefacto `.md` descargable.

---

## `PLAN_INLINE_ONLY`

Hay contenido que parece un plan, pero solo inline y no como archivo válido.

---

## `PLAN_ARTIFACT_MISSING`

La respuesta debería producir un archivo, pero no existe un artefacto utilizable.

---

## `SELF_CONTINUE`

ChatGPT indicó que todavía debe continuar su propio trabajo.

El controller puede enviar exactamente:

```text
procede
```

una sola vez para ese fingerprint.

---

## `FINAL_GO`

ChatGPT declara explícitamente GO/COMPLETE_GO.

El controller aún debe validarlo.

---

## `HUMAN_BLOCKED`

Existe una dependencia que realmente requiere intervención humana.

---

## `NO_CHANGE`

No existe una transición clara.

---

# 19. Fingerprints semánticos

El controller genera fingerprints para identificar una respuesta.

Esto impide repetir:

- el mismo `procede`;
- el mismo request de diagnóstico;
- el mismo replan;
- la misma acción;
- el mismo follow-up.

El principio es:

```text
una transición lógica por respuesta física
```

---

# 20. Cómo se transporta una acción del chat al sistema operativo

Supongamos que ChatGPT responde:

```text
action id: B01
target=local
timeout_seconds=180

```bash
python3 -m unittest ...
```
```

El flujo seguro es:

```text
ChatGPT DOM
   ↓
Browser Broker identifica fenced blocks
   ↓
metadatos:
  block_index
  SHA-256
  bytes
   ↓
OpenCode selecciona semánticamente el bloque correcto
   ↓
controller solicita MATERIALIZE_CODE_BLOCK
   ↓
broker vuelve al DOM
   ↓
extrae textContent exacto
   ↓
verifica SHA y tamaño
   ↓
escribe archivo controlado
   ↓
controller vuelve a verificar
   ↓
ejecución
```

Los bytes del comando no dependen de que el LLM los vuelva a transcribir.

---

# 21. Targets de una acción

Actualmente las acciones de operator se clasifican en:

```text
local
vps
github-readonly
```

Semaphore se maneja como integración determinista especializada.

---

# 22. Acción `local`

Se ejecuta aproximadamente como:

```bash
bash -lc '<command>'
```

con:

```text
cwd = repositorio local
```

Repositorio esperado:

```text
/mnt/d/works/bot_trad/bot_trading
```

---

# 23. Acción `vps`

No se permite SSH arbitrario desde la acción.

El controller ejecuta:

```text
/opt/ai-loop/bin/vps-ssh '<remote command>'
```

Esto concentra:

- autenticación;
- host;
- política;
- transporte;
- auditoría.

---

# 24. Acción `github-readonly`

Está diseñada únicamente para inspección.

Se bloquean mutaciones como:

```text
gh pr merge
gh pr create
gh issue create
gh release create
gh repo edit
gh api POST/PUT/PATCH/DELETE
git push
git commit
git tag
```

---

# 25. Comandos prohibidos en operator

La política bloquea, entre otros:

```text
git commit
git push
git reset
git clean
shutdown
reboot
raw ssh/scp/sftp
rm -rf arbitrario
```

Existe una excepción estrecha a `rm -rf` para un patrón controlado de directorio temporal:

```bash
TMP="$(mktemp -d /tmp/<safe>.XXXXXX)"
trap cleanup EXIT
rm -rf "$TMP"
```

---

# 26. Invariante especial de `/tmp/log`

El operator no debe modificar:

```text
/tmp/log
```

Se bloquean operaciones como:

```text
rm
mv
touch
truncate
chmod
chown
tee
redirección >
redirección >>
```

sobre ese árbol.

Leerlo, hashearlo o copiarlo **como fuente** puede permitirse.

---

# 27. Persistencia de resultados de acciones

Cada acción ejecutada se guarda en:

```text
/var/lib/ai-loop/runs/<RUN_ID>/actions/
```

El JSON incluye:

- id;
- target;
- command;
- start time;
- finish time;
- exit code;
- stdout;
- stderr;
- timeout.

Si el controller reinicia y ya existe un resultado válido, puede reutilizarlo en vez de repetir la acción.

---

# 28. Cómo se devuelven resultados a ChatGPT

Los resultados se convierten en bloques como:

```text
===== ACTION B01 target=local =====
COMMAND:
...
EXIT_STATUS=0
TIMED_OUT=false
--- STDOUT ---
...
--- STDERR ---
...
===== END B01 =====
```

Si todo cabe dentro del límite de evidencia inline, se envía en el mensaje.

Si es demasiado grande, se genera:

```text
operator-evidence-<timestamp>.txt
```

y se adjunta.

---

# 29. Detección de un nuevo candidato Git

El controller consulta GitHub con:

```text
gh api repos/<repo>/commits/<branch> --jq .sha
```

La función tiene retries para errores de red transitorios.

Se compara:

```text
HEAD remoto
vs.
baseline_sha
```

Cuando cambia:

```text
candidate_sha = HEAD
phase = WAIT_CI
```

---

# 30. `baseline_sha`

Es el SHA de `feature/GRU` cuando comienza una iteración de implementación.

Permite responder:

```text
¿apareció realmente un commit nuevo?
```

---

# 31. `candidate_sha`

Es el SHA nuevo detectado después de la implementación.

Una vez definido, CI y GO deben referirse a ese SHA exacto.

---

# 32. Monitoreo CI

La función:

```text
ci_status(candidate_sha)
```

invoca el helper:

```text
/opt/ai-loop/bin/ci-status <sha>
```

Ese helper debe devolver JSON indicando al menos estado y datos del provider.

Estados lógicos:

```text
PENDING
RUNNING
QUEUED
UNKNOWN
SUCCESS
FAILURE
```

---

# 33. Si CI sigue ejecutándose

En fase:

```text
WAIT_CI
```

si CI devuelve:

```text
PENDING / RUNNING / QUEUED / UNKNOWN
```

el controller espera y vuelve a consultar.

No molesta al chat durante esa espera.

---

# 34. Si CI termina exitosamente

Transición:

```text
WAIT_CI
   ↓
FINAL_REVIEW
```

El controller envía al chat información del candidato exacto:

```text
candidate_sha
provider
run_id
pipeline_id
```

y pide una revisión final sin nuevos commits.

---

# 35. Si CI falla

Transición:

```text
WAIT_CI
   ↓
FAILURE_ANALYSIS
```

con:

```text
failure_stage = EVIDENCE_COLLECTING
```

Si el provider es Semaphore, comienza una ruta especial.

---

# 36. Evidencia Semaphore

Para Semaphore el sistema exige identidad exacta:

```text
provider
candidate SHA
run id
pipeline id
```

Se calcula una clave estable de fallo.

La evidencia se guarda bajo:

```text
/var/lib/ai-loop/runs/<RUN_ID>/ci/semaphore/
```

---

# 37. Acceso read-only a Semaphore

El Browser Broker puede:

1. abrir Semaphore;
2. comprobar si ya está autenticado;
3. intentar login mediante GitHub;
4. buscar SHA/run/pipeline exactos;
5. leer estado;
6. devolver evidencia.

Si aparece:

```text
password
OTP
2FA
device authorization
```

puede devolver:

```text
AUTH_REQUIRED_HUMAN
```

en lugar de inventar éxito.

---

# 38. Reproducción local de un fallo CI

Después de obtener evidencia del job fallido, ai-loop puede hacer una investigación local exacta.

Crea un clone temporal y hace:

```text
git clone --no-checkout
git checkout --detach <candidate_sha>
```

Luego:

- comprueba HEAD;
- parent;
- tree;
- worktree clean;
- busca YAML de Semaphore;
- identifica el job fallido;
- extrae comandos potencialmente reproducibles.

---

# 39. Qué comandos de CI se pueden reproducir

Solo comandos de validación considerados seguros, por ejemplo:

```text
python -m unittest
pytest
py_compile
bash -n
compileall
```

Se bloquean comandos que involucren:

```text
ssh
scp
curl
wget
gh
Semaphore
sudo
systemctl
docker
kubectl
mysql
psql
git push
git commit
apt
npm install
pip install
mutaciones filesystem
```

La reproducción local no debe cambiar producción ni CI.

---

# 40. Diagnóstico después de fallo

Cuando la evidencia ya fue entregada al chat, el loop espera la respuesta.

Si la respuesta semántica es `NO_CHANGE`, puede enviar el prompt:

```text
/skillsbench the best diagnosis with the list of all granular causes of the last failure in .md file with datetime in filename
```

La intención es separar:

```text
evidencia
→ diagnóstico
→ plan
→ implementación
```

---

# 41. Replan

Cuando se detecta:

```text
DIAGNOSIS_READY
```

se envía `/ralplan`.

El prompt exige:

- plan completo;
- pasar Semaphore;
- llegar a COMPLETE_GO;
- evitar commits adicionales innecesarios;
- pruebas deterministas antes de gastar CI;
- team size;
- roles;
- backlog atómico;
- archivo `.md` descargable;
- timestamp en el filename.

---

# 42. Por qué el plan debe ser un archivo `.md` real

El contenido inline no es suficiente para la siguiente implementación.

El contrato exige un artefacto físico descargable porque:

- tiene bytes verificables;
- puede hashearse;
- puede guardarse;
- puede pasarse sin reinterpretación;
- se reduce el riesgo de que el siguiente chat reciba una transcripción parcial.

---

# 43. Descarga de artefactos

El broker/worker intenta localizar un `.md` real.

Puede inspeccionar:

- `href`;
- `blob:`;
- `data:`;
- downloads;
- preview;
- network resources.

Una vez descargado:

```text
bytes
SHA-256
UTF-8
estructura del plan
```

son validados.

---

# 44. Qué pasa después de descargar un nuevo plan

El estado hace:

```text
iteration += 1
baseline_sha = HEAD actual
candidate_sha = None
phase = IMPLEMENTING
```

Luego:

```text
nuevo chat
→ nuevo plan adjunto
→ nueva implementación
```

Eso permite múltiples iteraciones automáticas.

---

# 45. Fases principales del FSM

El controlador usa una máquina de estados.

## `IMPLEMENTING`

Estado normal mientras ChatGPT implementa y/o solicita acciones.

---

## `WAIT_CI`

Existe `candidate_sha` y se espera CI.

---

## `FAILURE_ANALYSIS`

CI falló.

Se recolecta evidencia y se coordina:

```text
evidence
→ diagnosis
→ replan
→ plan artifact
```

---

## `FINAL_REVIEW`

CI pasó y se espera confirmación final.

---

## `DONE`

GO validado determinísticamente.

---

# 46. `failure_stage`

Dentro de `FAILURE_ANALYSIS` existe una submáquina.

Algunos stages históricos/actuales son:

```text
EVIDENCE_COLLECTING
EVIDENCE_DELIVERED
DIAGNOSIS_SENT
REPLAN_SENT
PLAN_TEXT_REQUESTED
PLAN_ARTIFACT_REQUESTED
PLAN_ARTIFACT_REPAIR_REQUIRED
PLAN_ARTIFACT_CORRECTIVE_REQUIRED
PLAN_ARTIFACT_WAIT_NEW_MESSAGE
PLAN_ARTIFACT_BLOCKED
PLAN_ARTIFACT_BLOCKED_FINAL
```

Su objetivo es impedir que la ruta de recuperación se mezcle con follow-ups genéricos.

---

# 47. Condiciones para aceptar GO

ChatGPT no puede decidir GO por sí solo.

Cuando se observa:

```text
GO
```

el controller comprueba:

```text
candidate_sha existe
GitHub HEAD == candidate_sha
CI(candidate_sha) == SUCCESS
```

Solo si todo coincide:

```text
phase = DONE
```

y escribe:

```text
/var/lib/ai-loop/state/go_confirmed.json
```

---

# 48. Por qué se conserva `ai-loopd-v3.py`

Los nombres:

```text
ai-loopd-v3.py
start-loop-v3
stop-loop-v3
...
```

se conservan por compatibilidad operacional.

No significan que la versión sea v3.

La versión real se ve en el log:

```text
ai-loopd-v3 version=4.2.0
```

---

# 49. Estructura del paquete v4.2

```text
ai-loop-v4.2/
├── ai-loopd-v3.py
├── browser-broker-v1.cjs
├── playwright-artifact-worker.cjs
├── playwright-bootstrap-observer.cjs
├── playwright-bootstrap-worker.cjs
├── install.sh
├── README.md
├── OPERATOR_POLICY_V3.md
├── operator-transport.md
├── AI_LOOP_FULL_ACCEPTANCE_....md
├── IMPLEMENTATION_PLAN_AI_LOOP_V4_1_....md
├── IMPLEMENTATION_REPORT_V4_1.md
├── KNOWN_LOG_FINDINGS_COVERAGE.md
├── ANALYSIS_ROOT_CAUSE_....md
├── selftest-v4.py
├── selftest-v4.1.py
├── selftest-v4.2.py
├── tests/
│   ├── test-browser-broker-v4.2.cjs
│   └── ui-drift-fixtures.json
├── bin/
│   ├── start-loop-v3
│   ├── stop-loop-v3
│   ├── status-loop-v3
│   ├── restart-loop-v3
│   ├── resume-current-v3
│   ├── kill-all-loop-v3
│   ├── preflight-v4.1
│   ├── preflight-v4.2
│   ├── verify-v4.1-local
│   └── verify-v4.2-local
└── prompts/
    ├── implement.txt
    ├── diagnosis.txt
    ├── replan.txt
    ├── no_commit_followup.txt
    ├── operator_capabilities.txt
    └── plan_artifact_followup.txt
```

---

# 50. Directorios instalados

## `/opt/ai-loop`

Código y configuración activa:

```text
/opt/ai-loop/
├── ai-loopd-v3.py
├── browser-broker-v1.cjs
├── playwright-*.cjs
├── project.yaml
├── ai-loop.env
├── OPERATOR_POLICY_V3.md
├── prompts/
└── bin/
```

---

## `/var/lib/ai-loop/state`

Estados durables:

```text
R....v3.json
R....v3.pid
.ai-loopd.global.lock
go_confirmed.json
```

---

## `/var/lib/ai-loop/logs`

Logs:

```text
R....v3.log
opencode-v3.log
```

---

## `/var/lib/ai-loop/runs/<RUN_ID>`

Evidencia específica de cada run:

```text
actions/
browser/
ci/
plan-handoff/
action-handoff/
...
```

---

# 51. `project.yaml`

Configuración mínima típica:

```yaml
repo: Trochez/bot_trading
branch: feature/GRU

chatgpt:
  project_url: https://chatgpt.com/g/g-p-...-bot-trading

operator:
  default_model: omniroute/codex/gpt-5.6-luna

vps:
  ssh_host: production

storage:
  runs: /var/lib/ai-loop/runs
  state: /var/lib/ai-loop/state
```

El parser actual lee directamente:

```text
repo
branch
project_url
```

El repo local por defecto es:

```text
/mnt/d/works/bot_trad/bot_trading
```

---

# 52. `ai-loop.env`

`install.sh` configura variables importantes.

Entre ellas:

```text
OPENCODE_TRANSPORT_AGENT=operator

AI_LOOP_PLAYWRIGHT_UPLOAD_ROOT=...
AI_LOOP_BROWSER_PROFILE=...
AI_LOOP_OPENCODE_CLI_DIR=/mnt/d/works/ai-control-plane
AI_LOOP_DOM_HANDOFF_ROOT=...

AI_LOOP_ARTIFACT_WORKER=/opt/ai-loop/playwright-artifact-worker.cjs
AI_LOOP_BOOTSTRAP_OBSERVER_WORKER=...
AI_LOOP_BOOTSTRAP_WORKER=...
AI_LOOP_BROWSER_BROKER=/opt/ai-loop/browser-broker-v1.cjs

AI_LOOP_CHROME_EXECUTABLE=/opt/google/chrome/chrome

AI_LOOP_BROWSER_ACTION_TIMEOUT_MS=8000
AI_LOOP_BROWSER_NAVIGATION_TIMEOUT_MS=30000
AI_LOOP_BROWSER_SETTLE_TIMEOUT_MS=12000
AI_LOOP_ASSISTANT_RESPONSE_TIMEOUT_MS=900000

AI_LOOP_MIN_SEND_INTERVAL_SECONDS=5
AI_LOOP_STARTUP_QUIET_SECONDS=0
AI_LOOP_GENERATING_POLL_BASE_SECONDS=5
AI_LOOP_GENERATING_POLL_MAX_SECONDS=30
```

---

# 53. Rate limits y anti-spam

Además existen variables como:

```text
AI_LOOP_RATE_LIMIT_BASE_SECONDS
AI_LOOP_RATE_LIMIT_STEP_SECONDS
AI_LOOP_MIN_SEND_INTERVAL_SECONDS
```

El controller mantiene:

```text
last_send_epoch
next_send_not_before_epoch
rate_limit_until_epoch
rate_limit_streak
```

Antes de cada Send calcula cuándo está permitido el siguiente mensaje.

---

# 54. Respuestas todavía generándose

Si ChatGPT está generando, el sistema no debe enviar otro mensaje.

Usa polling progresivo:

```text
GENERATING
→ esperar
→ observar nuevamente
```

No interpreta una respuesta parcial como autoritativa.

---

# 55. Rate limit

Si se detecta rate limit:

```text
RATE_LIMIT
```

el controller incrementa un backoff y espera.

No intenta sortear el límite cambiando a Work/Codex.

---

# 56. Follow-up `procede`

Cuando ChatGPT ha dejado claro que puede continuar por sí mismo pero espera otra interacción, el semantic event puede ser:

```text
SELF_CONTINUE
```

Se traduce a:

```text
CONTINUE
```

El controller envía:

```text
procede
```

solo una vez por fingerprint.

---

# 57. Follow-up cuando no hay commit

Existe un prompt:

```text
Que hace falta para que hagas el commit con toda la implementacion completa?
```

pero está limitado por guardas anti-spam.

No debe enviarse indefinidamente.

---

# 58. Operator capabilities bridge

Si ChatGPT cree que no dispone de terminal, el controller puede enviar una explicación explícita:

```text
Tienes disponible un operator terminal externo...
```

Le explica:

- dónde está el repo local;
- cómo se accede al VPS;
- qué puede ejecutar el operator;
- qué no puede hacer;
- cómo expresar acciones mediante bloques shell.

---

# 59. Estado durable

El JSON de estado conserva muchas piezas.

Conceptualmente:

```json
{
  "run_id": "...",
  "phase": "IMPLEMENTING",
  "baseline_sha": "...",
  "candidate_sha": null,
  "chat_url": "...",
  "iteration": 0,
  "pending_actions": {},
  "processed_actions": [],
  "delivered_actions": [],
  "last_ci": null,
  "semantic_history": [],
  "failure_stage": "",
  "go_confirmed": null
}
```

También conserva información de:

- rate limiting;
- browser;
- plan artifacts;
- errores;
- handoffs;
- evidence deliveries;
- fingerprints;
- idempotencia.

---

# 60. Global lock

Al arrancar, el daemon toma:

```text
/var/lib/ai-loop/state/.ai-loopd.global.lock
```

mediante `flock`.

Esto evita dos controllers simultáneos.

También existe un lock asociado al archivo de state.

---

# 61. Inicio de un run nuevo

Comando:

```bash
/opt/ai-loop/bin/start-loop-v3 /path/to/PLAN.md
```

El script:

1. comprueba que el plan existe;
2. carga `ai-loop.env`;
3. rechaza procesos residuales;
4. crea `RUN_ID`;
5. crea ruta de STATE;
6. crea ruta de LOG;
7. inicia el daemon con `nohup`;
8. guarda PID;
9. imprime rutas.

Ejemplo:

```text
RUN_ID=R20260922T...
PID=12345
STATE=/var/lib/ai-loop/state/R....v3.json
LOG=/var/lib/ai-loop/logs/R....v3.log
```

---

# 62. Preflight

Antes de iniciar:

```bash
/opt/ai-loop/bin/preflight-v4.2 /path/to/PLAN.md
```

Comprueba:

```text
python3
node
opencode
git
gh
/opt/ai-loop/bin/vps-ssh
/opt/ai-loop/project.yaml
project_url de bot_trading
version 4.2.0
Playwright Node root
ausencia de procesos residuales
```

---

# 63. Verificación local

Desde el paquete:

```bash
./bin/verify-v4.2-local
```

Debe terminar en:

```text
BROKER_TEST_V4_2=PASS
SELFTEST_V4_2_RELEASE_CANDIDATE_LOCAL=PASS
VERIFY_V4_2_LOCAL=PASS
```

---

# 64. Instalación

```bash
./install.sh
```

Antes de sobrescribir archivos, crea backups con timestamp.

Instala:

- Python daemon;
- browser broker;
- workers;
- binarios;
- policy;
- prompts;
- agent OpenCode;
- env.

Después ejecuta:

- `py_compile`;
- `node --check`;
- broker tests;
- selftests.

Resultado esperado:

```text
INSTALL_V4_2=PASS version=4.2.0
```

---

# 65. Matar todos los procesos del loop

```bash
/opt/ai-loop/bin/kill-all-loop-v3
```

El resultado esperado:

```text
AI_LOOP_KILL_ALL=PASS
```

Mata:

- controllers;
- `opencode run`;
- Playwright MCP residual;
- browser broker;
- Chrome asociado al perfil del loop.

---

# 66. Detener un run concreto

```bash
/opt/ai-loop/bin/stop-loop-v3
```

o pasando PIDFILE:

```bash
/opt/ai-loop/bin/stop-loop-v3 \
  /var/lib/ai-loop/state/R....v3.pid
```

---

# 67. Reiniciar/resumir el mismo run

```bash
/opt/ai-loop/bin/restart-loop-v3 \
  /var/lib/ai-loop/state/R....v3.json
```

Alias:

```bash
/opt/ai-loop/bin/resume-current-v3
```

Esto **no crea un run nuevo**.

Reutiliza el state existente y reconcilia antes de efectuar side effects.

---

# 68. Ver estado resumido

```bash
/opt/ai-loop/bin/status-loop-v3
```

Muestra campos como:

```text
run_id
phase
iteration
baseline_sha
candidate_sha
chat_url
last_ci
go_confirmed
adaptive_browser_version
pending_actions
```

---

# 69. Monitorear logs

Para el run más reciente:

```bash
tail -F "$(ls -1t /var/lib/ai-loop/logs/*.v3.log | head -1)"
```

Para uno concreto:

```bash
tail -F /var/lib/ai-loop/logs/R....v3.log
```

---

# 70. Log sano de arranque

La secuencia ideal debe parecerse a:

```text
ai-loopd-v3 version=4.2.0 ...
BROWSER_BROKER=PASS ...
PROJECT_CONTEXT PASS project=bot_trading ...
FRESH_PROJECT_DRAFT PASS turns=0
CHAT_SURFACE PASS surface=chat
MODEL_GUARD PASS model=gpt-5.6-sol reasoning=high
ATTACHMENT_GUARD PASS filename=...
DELIVERY_SENT ...
DELIVERY_PROOF PASS ...
```

---

# 71. Evidencia automática cuando falla el browser

El broker genera:

```text
/var/lib/ai-loop/runs/<RUN_ID>/browser/broker-diagnostics/
```

Con archivos:

```text
<timestamp>-<operation>.json
<timestamp>-<operation>.html
<timestamp>-<operation>.png
```

Esto permite inspeccionar:

- DOM real;
- screenshot;
- URL;
- proyecto;
- controles;
- turns;
- error.

---

# 72. Posibles resultados de fresh draft

## Caso 1: ya está en un draft nuevo correcto

Resultado:

```text
PASS
```

sin navegación adicional.

## Caso 2: está en chat histórico del proyecto correcto

v4.2 fuerza la raíz del proyecto.

## Caso 3: está fuera del proyecto

vuelve a `project_url`.

## Caso 4: un `New chat` genérico escapa del proyecto

reingresa al proyecto y vuelve a verificar.

## Caso 5: no puede demostrar draft nuevo

falla cerrado:

```text
FRESH_PROJECT_DRAFT_NOT_REACHED
```

y guarda diagnóstico.

---

# 73. Posibles resultados de model policy

## Ya está correcto

No toca nada.

## Está en Work/Codex

intenta cambiar a Chat.

## Modelo diferente

abre selector y elige Sol.

## Reasoning diferente

elige High.

## El click funciona pero no puede probar selección

falla:

```text
MODEL_POLICY_NOT_PROVEN_SELECTED_STATE
```

---

# 74. Posibles resultados del Send

## `PASS`

Marcador demostrado después del click.

## `ALREADY_SENT`

El marcador ya existe; no vuelve a enviar.

## `AMBIGUOUS_SEND`

El click pudo ocurrir pero no se pudo demostrar el turno.

Se prohíbe retry ciego.

## error antes del click

puede reintentarse si es seguro.

---

# 75. Posibles estados de respuesta

## `GENERATING`

Esperar.

## `RATE_LIMIT`

Backoff.

## `SETTLED`

Puede pasar a clasificación semántica.

## `NO_ASSISTANT`

Aún no hay respuesta.

---

# 76. Posibles resultados de operator action

## éxito

```text
exit_code = 0
```

Se envía stdout/stderr al chat.

## fallo command

```text
exit_code != 0
```

También se devuelve evidencia literal.

## timeout

```text
exit_code = 124
timed_out = true
```

## policy blocked

```text
exit_code = 126
POLICY_BLOCKED
```

## transport rejected

```text
exit_code = 125
TRANSPORT_REJECTED
```

---

# 77. Reinicio después de crash

El objetivo del state durable es que un crash no implique “empezar desde cero”.

Al reiniciar:

- revisa acciones pendientes;
- reutiliza resultados persistidos;
- comprueba deliveries;
- comprueba candidate SHA;
- comprueba CI;
- no repite side effects por defecto.

---

# 78. Planes e iteraciones

`iteration` empieza en:

```text
0
```

Cuando un fallo requiere un nuevo plan:

```text
iteration = 1
```

y así sucesivamente.

Cada plan aprobado abre un nuevo ciclo de implementación.

---

# 79. Qué significa “un loop completo”

No significa únicamente enviar el primer mensaje.

Un loop exitoso incluye:

```text
plan
→ chat
→ implementación
→ acciones externas
→ evidencia
→ commit
→ CI
→ final review
→ GO
```

o, si hay fallo:

```text
plan
→ implementación
→ commit
→ CI failure
→ evidence
→ diagnosis
→ replan
→ nuevo plan
→ nueva implementación
→ ...
→ GO
```

---

# 80. Canary de aceptación

El paquete incluye un plan especial:

```text
AI_LOOP_FULL_ACCEPTANCE_....md
```

Su objetivo es ejercitar el pipeline sin cambios destructivos de producción.

Debe validar:

- ChatGPT;
- browser broker;
- OpenCode;
- local;
- GitHub read-only;
- VPS wrapper;
- Semaphore;
- varios round-trips;
- FINAL_GO.

---

# 81. Por qué el canary es obligatorio

Los selftests pueden demostrar:

- parser;
- invariantes;
- fixtures;
- funciones;
- soak sintético.

Pero no pueden demostrar desde un sandbox que:

- la sesión real de ChatGPT sigue válida;
- la UI real no cambió;
- GitHub auth real funciona;
- el VPS es accesible;
- Semaphore real está autenticado.

Por eso el canary live es un gate diferente.

---

# 82. Pruebas de v4.2

El paquete incluye pruebas específicas de browser.

Entre ellas:

```text
historical target forces root
already fresh fast path
bounded fresh control fallback
fresh draft timeout regression
policy wait predicate
synthetic full-loop soak
```

También conserva la suite de v4.1.

---

# 83. UI drift fixtures

Existe:

```text
tests/ui-drift-fixtures.json
```

Su propósito es comprobar variaciones del DOM/UI.

Esto evita depender de un único selector rígido.

---

# 84. Filosofía fail-closed

Cuando existe duda en una operación con side effects, la preferencia es:

```text
NO hacer nada
```

en lugar de:

```text
hacerlo y asumir
```

Ejemplos:

- proyecto desconocido → no enviar;
- modelo no comprobado → no enviar;
- action hash incorrecto → no ejecutar;
- send ambiguo → no reintentar a ciegas;
- CI identity incompleta → no diagnosticar como exacta;
- plan no descargable → no iniciar implementación nueva.

---

# 85. Qué es un bloqueo humano legítimo

Un bloqueo humano es algo que el sistema no puede resolver con seguridad.

Ejemplos:

- 2FA de Semaphore;
- sesión ChatGPT expirada;
- login manual requerido;
- acceso revocado;
- credencial externa inexistente.

No debería etiquetarse como humano un bug del controller.

---

# 86. Qué cosas debe hacer ChatGPT Web

La intención original del sistema es que el ChatGPT Web del proyecto:

- implemente el plan;
- use su acceso/repositorio permitido para los cambios;
- produzca commit/push cuando corresponda;
- interprete evidencia;
- prepare diagnósticos;
- prepare planes;
- haga revisión final;
- declare GO cuando corresponda.

El operator externo no sustituye esa autoridad de implementación.

---

# 87. Qué cosas debe hacer el controller

El controller:

- controla el protocolo;
- ejecuta comandos externos permitidos;
- verifica bytes;
- verifica estado;
- verifica CI;
- verifica SHA;
- verifica browser;
- controla idempotencia;
- decide si una transición está permitida.

---

# 88. Qué cosas debe hacer OpenCode

OpenCode se limita a funciones que realmente requieren interpretación de lenguaje natural, principalmente:

- clasificar la respuesta;
- identificar intención;
- seleccionar un bloque entre varios candidatos.

El browser y los side effects importantes pertenecen al controller/broker.

---

# 89. Integraciones externas necesarias

Para funcionamiento completo se espera:

## ChatGPT

- sesión autenticada en el perfil dedicado;
- acceso al proyecto `bot_trading`.

## GitHub CLI

```text
gh
```

autenticado.

## Git

Repositorio local disponible.

## OpenCode

```text
opencode
```

instalado.

## Node + Playwright

Necesarios para Browser Broker.

## Chrome

Por defecto:

```text
/opt/google/chrome/chrome
```

## VPS wrapper

```text
/opt/ai-loop/bin/vps-ssh
```

## CI status helper

```text
/opt/ai-loop/bin/ci-status
```

## Semaphore

Sesión/autenticación disponible o capacidad de completar el login admitido.

---

# 90. Qué ocurre si GitHub falla temporalmente

`github_head()` hace varios intentos.

Ejemplo de error transitorio:

```text
unexpected EOF
```

No debería convertirse inmediatamente en conclusión lógica sobre el estado del repo.

---

# 91. Qué ocurre si OpenCode falla

Una clasificación semántica fallida no produce side effect.

El controller registra el error y puede reintentar la clasificación después.

Esto es seguro porque interpretar nuevamente texto no duplica una acción física.

---

# 92. Qué ocurre si el Browser Broker muere

El diseño busca:

- detectar que el broker no está disponible;
- relanzarlo;
- volver a observar estado;
- reconciliar antes de cualquier side effect.

El estado autoritativo no debe existir únicamente en memoria del broker.

---

# 93. Qué ocurre si el controller recibe SIGTERM

El handler:

1. registra señal;
2. detiene Browser Broker;
3. termina.

El state ya persistido permite restart.

---

# 94. Backups durante instalación

`install.sh` copia versiones existentes a:

```text
<archivo>.bak.<timestamp>
```

antes de reemplazarlas.

Eso permite inspección/rollback manual.

---

# 95. Versiones históricas y compatibilidad

El proyecto fue evolucionando desde v2.x y v3.x.

Por eso todavía existen:

- funciones legacy;
- migraciones de state;
- nombres v3;
- workers legacy.

v4.x intenta mantener capacidad de leer estados anteriores sin perder:

- deliveries;
- pending actions;
- evidence;
- plan artifacts;
- candidate SHA.

No debe confundirse “código legacy conservado” con “ruta principal actual”.

La ruta principal v4.2 usa Browser Broker persistente.

---

# 96. Diferencia entre iniciar y reanudar

## Nuevo loop

```bash
start-loop-v3 PLAN.md
```

Crea:

- nuevo RUN_ID;
- state nuevo;
- chat nuevo.

## Reanudar

```bash
restart-loop-v3 STATE.json
```

Conserva:

- RUN_ID;
- estado;
- chat;
- candidate;
- acciones;
- evidencias.

---

# 97. Nunca usar restart para “empezar de cero”

Si la intención es un loop completamente nuevo con otro plan:

```text
usar start-loop-v3
```

No:

```text
restart-loop-v3
```

---

# 98. Cómo interpretar un traceback

Un traceback del controller indica un fallo técnico del loop.

Ejemplos:

```text
FRESH_PROJECT_DRAFT_NOT_REACHED
MODEL_POLICY_NOT_PROVEN_SELECTED_STATE
CHATGPT_AMBIGUOUS_SEND_UNRESOLVED_DIRECT
```

No debe tratarse como:

```text
ChatGPT terminó
```

ni como:

```text
GO
```

Hay que consultar el diagnóstico asociado.

---

# 99. Diagnóstico práctico de un fallo browser

Cuando aparece una ruta:

```text
evidence={"diagnostics": {...}}
```

revisar en este orden:

1. JSON;
2. screenshot;
3. HTML.

Ejemplo:

```bash
cat /var/lib/ai-loop/runs/<RUN>/browser/broker-diagnostics/<file>.json
```

Para screenshot:

```text
<same-stem>.png
```

El JSON suele ser la fuente más rápida para saber:

- URL;
- proyecto;
- turns;
- señales;
- error.

---

# 100. Diagnóstico práctico de una acción

Revisar:

```text
/var/lib/ai-loop/runs/<RUN>/actions/
```

El JSON contiene la evidencia de ejecución real.

---

# 101. Diagnóstico práctico de CI

Revisar:

```text
/var/lib/ai-loop/runs/<RUN>/ci/
```

Especialmente:

```text
ci/semaphore/
ci/local-reproduction/
```

---

# 102. Errores que no deberían reaparecer

La arquitectura actual intenta eliminar las familias históricas:

```text
ACTION_PAYLOAD_BASE64_INVALID
ACTION_PAYLOAD_UTF8_INVALID
ACTION_PAYLOAD_SHA256_MISMATCH
ADAPTIVE_PLAYWRIGHT_PROOF_MISSING
FRESH_PROJECT_CHAT ... UNVERIFIED
FRESH_BOOTSTRAP_JSON_INVALID
NEW_CHAT_POLICY_NOT_PROVEN
implicit local->vps
blind resend after possible Send
```

Un error nuevo debe diagnosticarse con evidencia actual, no arreglarse volviendo a los mecanismos que ya se retiraron.

---

# 103. Límites reales del sistema

Aunque el proyecto busca autonomía completa, no puede garantizar que servicios externos nunca cambien.

Pueden aparecer:

- UI nueva de ChatGPT;
- nueva política de autenticación;
- CAPTCHA;
- 2FA;
- outage;
- API de GitHub caída;
- Semaphore inaccesible;
- VPS sin red;
- repo con estado inesperado.

La obligación del controller es:

```text
detectar
registrar
preservar estado
evitar duplicados
fallar cerrado
```

no fingir éxito.

---

# 104. Regla operacional principal

Para cada side effect:

```text
observe
→ verify
→ persist intent
→ execute once
→ verify result
→ persist result
```

Nunca:

```text
execute
→ si no sé qué pasó, ejecutar otra vez
```

---

# 105. Secuencia completa: caso exitoso

```text
1. operador humano instala versión
2. mata loops viejos
3. preflight
4. start-loop-v3 PLAN.md
5. controller crea RUN_ID
6. controller guarda baseline SHA
7. inicia Browser Broker
8. broker abre proyecto
9. broker crea fresh draft
10. broker garantiza Chat/Sol/High
11. broker adjunta plan
12. broker escribe delivery marker + implementación
13. SEND_ATOMIC
14. browser prueba user turn
15. controller observa respuesta
16. ChatGPT implementa
17. si solicita tests:
      broker extrae blocks
      OpenCode selecciona
      controller materializa
      controller ejecuta
18. controller devuelve evidencia
19. ChatGPT termina cambios/commit/push
20. GitHub HEAD cambia
21. candidate_sha = nuevo HEAD
22. phase = WAIT_CI
23. ci-status reporta SUCCESS
24. phase = FINAL_REVIEW
25. controller solicita revisión final
26. ChatGPT declara GO
27. controller valida:
      HEAD == candidate
      CI(candidate) == SUCCESS
28. phase = DONE
29. escribe go_confirmed.json
30. loop termina
```

---

# 106. Secuencia completa: CI falla una vez

```text
1–21. igual al caso exitoso
22. WAIT_CI
23. CI = FAILURE
24. FAILURE_ANALYSIS
25. recolectar Semaphore evidence
26. reproducir validaciones seguras localmente
27. enviar evidencia a ChatGPT
28. ChatGPT pide/produce diagnóstico
29. DIAGNOSIS_READY
30. enviar /ralplan
31. PLAN_READY
32. descargar .md
33. verificar bytes/hash/estructura
34. iteration += 1
35. baseline = HEAD actual
36. candidate = None
37. nuevo chat
38. implementar nuevo plan
39. nuevo candidate
40. CI SUCCESS
41. FINAL_REVIEW
42. GO
43. DONE
```

---

# 107. Secuencia completa: ChatGPT solicita comando remoto

```text
assistant response
→ semantic event OPERATOR_ACTION_REQUESTED
→ fenced block identificado
→ block index + SHA + bytes
→ target=vps
→ MATERIALIZE_CODE_BLOCK
→ verify SHA/bytes
→ policy check
→ /opt/ai-loop/bin/vps-ssh <command>
→ stdout/stderr/rc persistidos
→ evidence enviado al mismo chat
→ observar nueva respuesta
```

---

# 108. Secuencia completa: Send ambiguo

```text
READY
→ SENDING
→ click
→ no aparece marker dentro del timeout
→ AMBIGUOUS_SEND
→ NO second click
→ OBSERVE_DELIVERY
→ buscar marker
```

Si se encuentra:

```text
reconciliar como ALREADY_SENT
```

Si no:

```text
bloqueo explícito
```

---

# 109. Secuencia completa: artifact faltante

```text
PLAN_READY semántico
→ download attempt
→ no .md válido
→ no nueva implementación
→ bounded retries
→ corrective request / artifact follow-up
→ esperar nuevo mensaje
→ descargar bytes reales
```

---

# 110. Invariantes que una modificación futura no debe romper

1. un nuevo loop no escribe en chat histórico;
2. proyecto debe probarse;
3. Chat/Sol/High debe probarse;
4. OpenCode no es dueño de Send;
5. command bytes no pasan por LLM como autoridad;
6. acción se verifica antes de ejecutar;
7. local no se redirige implícitamente a VPS;
8. GitHub read-only sigue read-only;
9. no blind resend;
10. no blind action retry;
11. CI se liga a SHA exacto;
12. GO se valida fuera del modelo;
13. un plan de remediación debe ser archivo real;
14. estado se persiste antes/después de side effects;
15. un run solo tiene un controller/browser owner.

---

# 111. Procedimiento recomendado para uso diario

## 1. Verificar que no exista otro loop

```bash
/opt/ai-loop/bin/kill-all-loop-v3
```

## 2. Preflight

```bash
/opt/ai-loop/bin/preflight-v4.2 /path/to/PLAN.md
```

## 3. Start

```bash
/opt/ai-loop/bin/start-loop-v3 /path/to/PLAN.md
```

## 4. Monitor

```bash
tail -F "$(ls -1t /var/lib/ai-loop/logs/*.v3.log | head -1)"
```

## 5. Estado resumido

En otra terminal:

```bash
/opt/ai-loop/bin/status-loop-v3
```

## 6. Si necesitas detenerlo

```bash
/opt/ai-loop/bin/stop-loop-v3
```

## 7. Si quieres continuar exactamente el mismo run

```bash
/opt/ai-loop/bin/restart-loop-v3 /var/lib/ai-loop/state/<RUN>.v3.json
```

---

# 112. Checklist de un run sano

Antes del primer Send:

```text
[ ] BROWSER_BROKER PASS
[ ] target project = bot_trading
[ ] fresh draft
[ ] user turns = 0
[ ] assistant turns = 0
[ ] Chat selected
[ ] GPT-5.6 Sol selected
[ ] High selected
[ ] plan attached
[ ] delivery marker unique
```

Después:

```text
[ ] marker visible como user turn
[ ] response observable
[ ] semantic event válido
[ ] acciones verificadas por SHA
[ ] evidence enviada una sola vez
[ ] candidate SHA exacto
[ ] CI ligado al SHA exacto
[ ] final GO validado
```

---

# 113. Checklist antes de aceptar una nueva release de ai-loop

```text
[ ] py_compile
[ ] node --check
[ ] broker tests
[ ] selftests
[ ] UI drift fixtures
[ ] synthetic soak
[ ] safe live canary
[ ] no wrong-project sends
[ ] no duplicate sends
[ ] no duplicate actions
[ ] no uncaught traceback
[ ] actual plan reaches GO or external human-only blocker
```

---

# 114. Glosario

## Run

Una ejecución concreta del controller.

Ejemplo:

```text
R20260922T022054
```

## Iteration

Una implementación generada a partir de un plan dentro del mismo proceso global de remediación.

## Baseline SHA

SHA inicial de la iteración.

## Candidate SHA

SHA nuevo que debe ser validado por CI.

## Delivery ID

Identificador de un mensaje enviado por el controller.

## Fingerprint

Identidad estable de una respuesta/transición para idempotencia.

## Broker

Proceso Playwright persistente dueño del navegador.

## Operator

Capa externa que ejecuta comandos controlados.

## Semantic event

Interpretación estructurada del significado de una respuesta de ChatGPT.

## Artifact

Archivo físico, por ejemplo un plan `.md`.

## Evidence

Prueba literal de una acción/estado.

## Fail-closed

Ante duda, no realizar el side effect.

---

# 115. Qué hace que este proyecto sea “agentic”

El sistema no ejecuta un guion fijo de principio a fin.

Puede reaccionar a:

```text
implementación incompleta
acción solicitada
evidencia solicitada
generación larga
rate limit
commit nuevo
CI pending
CI success
CI failure
diagnóstico
nuevo plan
bloqueo humano
final GO
```

Pero esa autonomía está limitada por una FSM y por verificadores deterministas.

Esa combinación es precisamente la diferencia entre:

```text
un script de automatización
```

y:

```text
un pipeline agentic controlado
```

---

# 116. Resumen final

`ai-loop` puede entenderse como un **orquestador autónomo de ingeniería de software**.

GPT-5.6 Sol Web hace el trabajo intelectual principal de implementación y revisión. OpenCode ayuda a interpretar lenguaje natural. El controller Python dirige el ciclo. El Browser Broker posee el navegador y comprueba el estado real de ChatGPT. GitHub y CI sirven como fuente externa de verdad del código. El operator ejecuta comandos seguros y devuelve evidencia. El VPS y Semaphore proporcionan validación operacional.

La arquitectura completa está diseñada alrededor de una regla:

> Ninguna afirmación de un modelo debe transformarse en un efecto irreversible sin que el controlador pueda demostrar qué estado existía antes, qué operación ocurrió y qué estado existe después.

Por eso el proyecto guarda states, logs, hashes, delivery IDs, evidencia, candidate SHAs y CI identities.

El loop está terminado solamente cuando el candidato exacto ha pasado CI y un GO explícito ha sido validado de forma independiente por el controlador.
