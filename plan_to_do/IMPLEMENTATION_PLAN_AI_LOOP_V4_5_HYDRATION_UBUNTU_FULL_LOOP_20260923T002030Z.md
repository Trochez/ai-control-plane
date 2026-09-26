# Plan ai-loop v4.5 — hidratación correcta, Ubuntu Server y ciclo completo demostrado

**Fecha base:** 2026-09-23T00:20:30Z / 2026-09-22T19:20:30-05:00 (Colombia).  
**Base inspeccionada:** paquete `ai-loop-v4.3/` del tar adjunto; declara `VERSION = '4.4.0'`.  
**Release propuesta:** `4.5.0`; conservar entrypoints operacionales `*-v3` compatibles.  
**Incidente:** `R20260922T160843`, fallo de startup a las 00:11Z del 23 de septiembre.  
**Método:** `omo-ralplan` adjunta en `SKILL(6).md`, deliberate, sin interacción de aprobación intermedia.  
**Estado:** aprobado tras revisión secuencial Arquitecto → Crítico; listo para implementación.
**Entrega solicitada:** planificación; no se ha instalado una corrección ni ejecutado aceptación live en el servidor del usuario.

## 1. Objetivo y condición obligatoria de cierre

Entregar una versión que complete un ciclo real y autónomo en **Ubuntu Server con repositorio local**, usando ChatGPT Chat, browser broker, OpenCode, ejecución local, GitHub, wrapper VPS, Semaphore/CI, transporte de archivos y revisión final. Debe demostrar:

1. Arranque nuevo y reanudación del run existente sin `CHAT_SURFACE_HYDRATION_TIMEOUT` prematuro.
2. Plan adjunto una sola vez, envío demostrado, respuesta finalizada, acciones explícitas ejecutadas y evidencia devuelta al mismo chat.
3. Implementación realizada por el escritor autorizado, candidato atribuible, CI completo del SHA exacto y `GO` validado por código.
4. Recuperación real de CI fallido: logs → diagnóstico → plan `.md` descargado → nuevo chat/iteración → nueva implementación → CI exitoso → GO.
5. Reinicios en puntos de efecto sin envíos, acciones ni commits duplicados.

**No cerrar por compilación, selftests, screenshots del selector o primer Send.** Cada defecto descubierto durante estas pruebas pertenece a esta implementación: evidencia → reproducción → corrección → regresión → repetición de gates afectados. Un bug interno no es un bloqueo humano aceptable. Dependencias externas genuinas se registran con checkpoint y se reanudan al restaurarse; mientras tanto la release sigue **no aceptada**.

La prueba read-only tiene un cierre propio, `READONLY_CANARY_PASS`, y no acredita una implementación. `IMPLEMENTATION_GO` exige un candidato nuevo y CI real. La aceptación final, `FULL_LOOP_ACCEPTED`, exige ambas rutas, recuperación, restart y objetivo real. No rebajar la guarda de GO para acomodar un canary incompatible.

## 2. Evidencia, alcance y diagnóstico fundamentado

### 2.1 Fuentes y límites

| Fuente | Resultado de inspección |
|---|---|
| Traceback proporcionado | `main:4859 → ensure_chat_policy:3288 → ENSURE_CHAT_POLICY → CHAT_SURFACE_HYDRATION_TIMEOUT`. OpenCode se recupera y broker arranca antes del fallo. |
| `ai-control-plane-current-20260923.tar.gz` | SHA-256 `6af6ce733c9017a8c22f2b1b257ab250c919259060ec99954ccd054433809a82`; 239 entradas; sin `.git` ni `AGENTS.md`. No inferir SHA Git del control plane. |
| Código activo del tar | `ai-loop-v4.3/ai-loopd-v3.py`, 5.683 líneas; broker, 447 líneas; versión lógica 4.4.0. Las referencias de línea de este plan corresponden a estos bytes. |
| Manifest incluido | 42 archivos coinciden y 7 difieren: README, daemon, preflight-v4.3, verify-v4.3-local, broker, install y selftest-v4.3. No prueba corrupción: prueba que el manifest está desactualizado respecto del tar. |
| Diagnósticos exactos actuales | Los archivos `2026-09-23T001147974Z-ENSURE_CHAT_POLICY.*` y `...001152437Z...` no están en el tar. Hay dos bundles de runs históricos `040029` y `042847`; no son evidencia del DOM actual. |
| Plan anterior dentro del tar | `plan_to_do/IMPLEMENTATION_PLAN_AI_LOOP_V4_4_LIVE_END_TO_END_RELIABILITY_20260922T1252-0500.md`; sus contratos se contrastaron con implementación y tests, sin heredar sus afirmaciones de éxito. |

El baseline `44505ddbfa5062dc1c712fc90db72cb0c54de924` pertenece al repo operado; **no es el SHA de esta reparación del control plane**. El host puede tener otros bytes: el primer gate compara fuente, runtime, configuración y evidence del incidente.

### 2.2 Causa reproducida del fallo de hidratación

En `browser-broker-v1.cjs:62`, `waitUntil` termina cuando su callback devuelve cualquier valor truthy. En `:251–252`, `ensurePolicy` entrega siempre el objeto producido por `policyState`, incluso cuando todas sus propiedades booleanas son falsas:

```javascript
const observe = async () => {
  const q = await this.policyState();
  timeline.push(/* observación */);
  return q; // objeto truthy aunque q.chat sea false
};
let state = await this.waitUntil(observe, this.timeouts.settle,
                                 'chat_policy_hydration');
```

La siguiente rama (`:253–254`) busca `Chat` una sola vez y, si aún no está, arroja el error llamado “timeout”. **No ha esperado la hidratación**. Aumentar el timeout no arregla este predicado.

Reproducción ejecutada sobre el método real, con dependencia `policyState` que anuncia Chat/High después de 200 ms, presupuesto 1.000 ms y sin navegador externo:

```json
{
  "error": "CHAT_SURFACE_HYDRATION_TIMEOUT",
  "policy_observations": 1,
  "click_attempts": 1,
  "elapsed_ms": 1,
  "settle_budget_ms": 1000
}
```

**Confirmado:** defecto de código y reproducción del mismo error por hidratación diferida. **Pendiente:** confirmar, con los diagnósticos actuales, si la UI del incidente era exactamente ese caso, otro layout, autenticación o selección duplicada. No atribuir el DOM no disponible a una causa única inventada.

Además, en `ai-loopd-v3.py:4859` la guarda de startup corre **antes** del `try` del ciclo principal (`:4866–4867`), por lo que las dos excepciones de policy escapan y terminan como traceback. Repetir el proceso no corrige el predicado ni conserva por sí solo una explicación durable de recuperación.

### 2.3 Hallazgos adicionales que amenazan el ciclo completo

`B` significa broker; `C` daemon, ambos dentro de `ai-loop-v4.3/`. Prioridad P0: bloqueo directo o riesgo de éxito/efecto incorrecto. P1: ruta obligatoria incompleta. “Estático” no implica reproducido live.

| ID | Prioridad / evidencia | Hallazgo y consecuencia |
|---|---|---|
| F01 | P0, reproducido; B:62,248–255 | Espera truthy; falso timeout inmediato de Chat. |
| F02 | P0, estático; C:3269–3288,4855–4867 | Startup fuera de frontera de recuperación; retry fijo termina en excepción sin protocolo de bloqueo/reanudación. |
| F03 | P1, reproducido; B:232,258–262 | `Chat` + `aria-label=Chat` se convierte en `Chat Chat` y no coincide con `/^Chat$/`; el trigger/menú High también se busca sin esperar aparición. |
| F04 | P1, reproducido; B:84,141–145 | `_freshTargetState` acepta `root_selector_kind='none'` si otro selector vio un editor; no exige `present` ni raíz probada. |
| F05 | P0/P1, estático; B:272–303,325–334 | Adjuntos se eliminan por controles globales; `ALREADY_ATTACHED` no comprueba `uploading`; ledger de upload queda solo en localStorage después del efecto. Send selecciona botón global y revalida proyecto, pero no policy/archivo/texto íntegros justo antes del click. |
| F06 | P1, estático; C:1131–1140; B:419 | Cada observación navega con `goto`, incluso a la misma URL: puede reiniciar hidratación y perturbar generación. URLs genéricas guardadas no identifican por sí solas el chat del run. |
| F07 | P1, estático; B:355–363,412–413 | Texto del assistant se aplana con `norm`; indicador de generación usa count sin visibilidad; bloques `pre code, pre` duplican contenedores. Falta contrato robusto de respuesta estable/origen y bloque único. |
| F08 | P1, reproducido/inspeccionado; B:398 | El regex contiene byte `0x08` (backspace), no el escape `\b`; `PLAN.md` sin “download/markdown” no pasa el filtro. Bloquea artefactos de replan válidos. |
| F09 | P0, estático | Canary vigente prohíbe commit/push, prompt `implement.txt` los pide y `semantic_allowed` solo admite FINAL_GO en FINAL_REVIEW (C:1432–1435). Sin cambio de HEAD no hay candidate (C:5323–5335), y GO sin candidato se ignora (C:5457–5465). |
| F10 | P0, estático; C:13,45,126–136; install.sh:84 | `repo_dir` del YAML se ignora y quedan rutas `/mnt/d/...`; installer vuelve a escribir ruta WSL. Impide portabilidad real a Ubuntu Server. |
| F11 | P1, estático; B:46; preflight/install | Chrome siempre headed; no selección/validación de display/headless. Faltan `ci-status` y `vps-ssh` en el paquete; preflight no valida ci-status, autenticación ni capacidades reales. |
| F12 | P0, estático; C:3514–3518,5328–5335,5460–5465 | JSON CI se acepta sin schema/identidad; rc no cero con stdout puede aceptarse. GO no compara `ci.sha` ni exige jobs/run/pipeline completos. |
| F13 | P1, estático; B:376–385; C:2473–2511 | Semaphore deriva estado del body global y copia SHA esperado como verificado; siempre retorna `failed_jobs=[]`. Investigación local puede reportar PASS sin haber reproducido nada. |
| F14 | P0, estático; C:3794–3810 | Acción se ejecuta antes de persistir resultado; ausencia de archivo/state dispara replay tras crash. La ventana requiere receipt y reconciliación, no simple set de procesados. |
| F15 | P1, estático; C:1500–1506,5617–5628 | Fingerprint y etapa `*_SENT` se consumen antes de que `guarded_send` confirme entrega; puede esperar una respuesta a un mensaje nunca enviado. |
| F16 | P1, estático; C:5328–5333,5374–5376 | WAIT_CI pendiente hace continue antes de inspeccionar mensajes nuevos; solicitudes necesarias local/VPS pueden quedar sin atender. |
| F17 | P1, estático; C:4857–4858,293–303 | Salud HTTP OpenCode se registra como capacidad semántica PASS; no demuestra modelo/agente/CLI operativos. Agent instalado `operator-transport` conserva instrucciones browser mientras config elige `operator`. |
| F18 | P0/P1, inspeccionado | `selftest-v4.3.py:86–97` llama “100 full loops” a diccionarios y dos funciones semánticas. La comprobación del predicado busca strings del source; no prueba hidratación. Manifest/versiones mezcladas debilitan trazabilidad. |
| F19 | P1, estático; C:444–526; B:415–447 | RPC envía deadline que broker no consume; timeout del cliente no cancela una operación pendiente. Shutdown usa `readline()` bloqueante antes de terminate; arranque fallido puede no limpiar `proc` local no registrado. |
| F20 | P1, estático; B:52–60,250–270 | Timeline solo se adjunta a una rama de error y `diag` no serializa `e.timeline`. El error inicial de hidratación pierde la cronología que explicaría el fallo. |

Otros riesgos a verificar dentro de estas tareas: inferencia de modelo por reasoning, project proof del sidebar, scripts de kill/preflight que alcanzan procesos ajenos y reejecución de milestones que solo se escriben pero no se reconcilian. No extender el refactor a módulos ya correctos sin evidencia.

### 2.4 Verificación ya ejecutada en esta planificación

Sobre el tar, con Python **3.12.14** y Node **v24.19.0**:

- `bash ai-loop-v4.3/bin/verify-v4.3-local`: rc **0**, `VERIFY_V4_4_LOCAL=PASS`.
- Prueba aislada de Chat tardío: falla en 1 ms y una observación, en vez de esperar 1.000 ms.
- Reasoning tardío: `REASONING_SELECTOR_NOT_FOUND` tras una observación.
- Raíz de composer ausente: `_freshTargetState` la acepta indebidamente en el caso controlado.
- Texto/label duplicados: `clickMatching(/^Chat$/i)` devuelve false con control visible `Chat`/`Chat`.
- Artefacto: byte 0x08 confirmado; el patrón no encuentra `PLAN.md` en el caso controlado.
- Verificación de manifest: 7 discrepancias listadas en §2.1.

Estos son resultados del análisis, no pruebas de una corrección. No se ejecutaron instalación, navegación autenticada, envíos, push, VPS ni CI del usuario.

## 3. RALPLAN-DR y decisión ADR-045

**Principios:** (1) observar condiciones reales antes de actuar; (2) preservar autoridad única del broker y política de Chat; (3) persistir/reconciliar efectos antes de repetir; (4) separar prueba read-only de aceptación de implementación; (5) probar el runtime real y su evidencia, no cadenas del source.

**Tres drivers:** resolver la regresión demostrada; completar todas las integraciones en Ubuntu Server; evitar duplicados y GO sin respaldo, con el menor cambio necesario.

| Alternativa | Ventaja | Límite | Decisión |
|---|---|---|---|
| A. Corregir únicamente `return q` y repetir | Diff mínimo; cierra F01 rápidamente | No resuelve F03, F09, Ubuntu ni gates falsos; puede trasladar el fallo a la fase siguiente | Primer incremento útil, entrega final insuficiente. |
| B. Reparación guiada por evidencia de readiness, binding, transacciones y contratos, más pruebas integrales | Corrige causas observadas y bloqueos demostrables; reutiliza componentes correctos | Mayor matriz de pruebas y coordinación de archivos compartidos | **Elegida**, por incrementos y `VERIFIED_EXISTING`. |
| C. Aumentar timeouts, agregar sleeps o más retries externos | Rápido de intentar | El objeto seguirá siendo truthy; no demuestra readiness ni corrige contradicción del canary | Rechazada como solución; calibrar presupuestos solo después de corregir predicados. |
| D. Reescribir todo o entregar browser al LLM | Flexibilidad aparente | Amplía alcance/autoridad, pierde invariantes y demora validación | Rechazada; no hace falta otro browser owner. |

**Decisión:** B. Hacer primero roja la regresión F01, implementar espera semántica limitada, cerrar contratos críticos de ciclo y ejecutar gates progresivos. Si un componente ya satisface una tarea, cerrarla `VERIFIED_EXISTING` con ruta/símbolo, prueba ejecutada y revisión; nunca solo por README o log PASS anterior.

**Consecuencias:** se versionan schemas de contexto, outbox, receipts y aceptación; cambia el canary y el empaquetado; se preserva compatibilidad operacional. Un bloqueo externo detiene la aceptación, no habilita bypass. **Follow-ups:** mantener fixtures de UI reales saneadas, manifest actualizado y métricas de cada fase.

## 4. Equipo: siete integrantes y ownership

**Tamaño total: 7, incluido el coordinador; 6 especialistas.** No se prescriben modelos. OpenCode `general` sirve para especialistas/revisores y `explore` para descubrimiento; verificar esos tipos disponibles. `task()` nativo no está expuesto en esta sesión: las revisiones usan colaboración disponible, no una ejecución fingida de OpenCode.

| ID | Rol | Propiedad principal | Razonamiento |
|---|---|---|---|
| TL | Coordinación/arquitectura | Contratos, alcance/repo, integración y gates | Alto/máximo para decisiones de arquitectura. |
| BR | Browser/DOM | Broker, readiness, composer, observer, downloads | Alto. |
| CT | Controller/FSM | Daemon, RPC, navegación/binding, outbox, recuperación, GO | Alto/máximo en crash/efectos. |
| IN | Integraciones | OpenCode, writer, GitHub, CI, Semaphore, VPS y prompts | Alto. |
| QA | Ingeniería de pruebas | Fixtures, runner multiproceso, faults, soak y regresiones | Alto. |
| SR | Ubuntu/operación/release | Config/rutas, display, perfiles, wrappers, install/rollback | Medio/alto; alto para migración. |
| AU | Auditor independiente | Evidencia, invariantes y aprobación final | Alto/máximo; no autoaprueba implementación propia. |

BR es dueño único del broker; CT del daemon. IN entrega contratos/adaptadores o patches coordinados; no edita a la vez las secciones de CT/BR. QA escribe tests, AU audita producto/resultados y TL revisa tests. SR opera instalación/browser live en ventanas exclusivas. El número del equipo no habilita siete sesiones Chrome contra el mismo perfil.

## 5. Diseño de la reparación del browser y startup

### 5.1 Readiness semántico y tiempos

`ensurePolicy` debe esperar **estado utilizable**, no cualquier snapshot:

1. Observar página/conversación/proyecto y clasificar: cargando, control disponible, Chat seleccionado, Work seleccionado, auth requerida, UI desconocida o error terminal.
2. Si Chat ya está seleccionado, continuar sin click. Si Work está activo y hay un único switcher Chat disponible, accionar y comprobar selección posterior. Si el switcher no existe todavía, volver a observar hasta deadline.
3. Esperar trigger de reasoning; después de abrir su menú, esperar opción autorizada visible/accionable; seleccionar y reobservar persistencia. Un click sin efecto no es PASS.
4. Revalidar Chat, reasoning y contrato de modelo juntos. Aceptar solo política configurada; no saltar a Work, Light, otro modelo o un reasoning distinto por conveniencia.
5. En timeout, persistir timeline completa y último estado; distinguir absent, disabled, ambiguous, auth y action-failed.

No basta sustituir el primer callback por `q.chat ? q : null`: eso impediría descubrir/accionar el switcher cuando Work está seleccionado. Separar **listo para inspección/cambio** de **política finalmente satisfecha**. Contrato conceptual:

```text
PENDING_HYDRATION → SURFACE_ACTIONABLE → CHAT_SELECTED
                  → REASONING_ACTIONABLE → POLICY_PROVEN
auth/error terminal → BLOCKED con evidencia
deadline agotado    → TIMEOUT con etapa, elapsed y timeline
```

Cada transición usa predicados verificables; no `networkidle` ni `domcontentloaded` como equivalente de app lista. Los localizadores usan rol/nombre accesible dentro del switcher/menú activo; no concatenar texto+aria+title ni elegir el primer match ambiguo. La UI puede mostrar controles antes de tener listeners: exigir postcondición observable tras el click [S1].

Presupuestos se leen de configuración, con reloj monotónico y deadline global de operación; respetar `deadline_epoch_ms` o sustituirlo por protocolo de presupuesto restante versionado. Reusar `AI_LOOP_BROWSER_*_TIMEOUT_MS` y añadir presupuesto de hydration solo si tiene semántica distinta. El efectivo no excede el tiempo RPC restante; no reiniciar el presupuesto en cada subpaso. Validar números, mínimos/máximos y guardar config efectiva. Ensayos con reloj controlado y un subconjunto de demora real prueban límites. Nada de sleeps fijos como reparación.

### 5.2 Contexto, modelo y reanudación

`project_url` configurado es autoridad de proyecto, no derivarlo solo de una URL genérica `https://chatgpt.com/`. Registrar `run_id`, iteration, project_id, tab/page binding, conversation_id/URL canónica, broker epoch y policy hash. En resume validar chat existente; no exigir cero turnos ni crear otro chat por un fallo de startup.

El código actual infiere nombre de modelo de Chat + High. El snapshot UI demuestra esos controles; **no demuestra por sí solo identidad de backend**. Preservar el contrato compatible que esté configurado y versionar `modelProof` como `explicit-ui` o `configured-ui-contract`, con evidencia y alcance. No introducir equivalencias nuevas ni afirmar verificación explícita cuando fue inferida. Si el requisito exige identidad explícita no observable, registrar esa carencia; no inventarla ni cambiar automáticamente de modelo. Revalidar variantes y superficie justo antes de enviar.

Configurar una allowlist de tipos de prueba admitidos. `configured-ui-contract` requiere ID/version/hash, procedencia y alcance autorizados en la configuración efectiva; conservar `observed_model_key` desconocido si la UI no lo expone y registrar por separado el contrato aceptado. Un marker heredado o Chat+High aislados no crean autorización ni identidad de modelo. La migración verifica esa procedencia; contrato desconocido/contradictorio bloquea la prueba hasta resolverlo.

Lecturas de una conversación ya enlazada no deben hacer `goto` repetido. Navegar solo ante ausencia real de la página o desvío comprobado; controlar normalización de URL sin mezclar conversaciones. Si bootstrap todavía está en ruta genérica, completar/reconciliar identidad mediante marcador y contexto antes de persistirla como reutilizable. Navegación, epoch o cambio de policy invalidan pruebas previas.

### 5.3 Composer, attachment y Send

Un solo resolver devuelve raíz/editor/send/attachments del composer **activo** con `present=true`, raíz permitida demostrada y binding. `none`/`unproven` bloquean. Nuevo run exige vacío y sin adjuntos; resume puede adoptar preparación del mismo run solo con hashes/ledger. Prohibido borrar adjuntos de otro composer o run.

Adjunto: persistir intención antes de upload; elegir input compatible por `accept` y control activo; tolerar que `input.files` se limpie si el chip/estado de upload prueba adopción. Reintento observa antes de subir; `ALREADY_ATTACHED` exige exactamente un archivo esperado, no uploading/error, binding vigente y fuente/hash coincidentes. Los sufijos de nombre no bastan para equivalencia; relacionar cambio de nombre con esa transacción. Guardar ledger del controller, no únicamente localStorage mutable de la página.

Pre-Send único dentro del broker: volver a comprobar proyecto/conversación, policy, adjunto esperado cuando aplique, texto/payload exacto, delivery_id y botón scoped habilitado; guardar `SENDING` durable, click una vez y buscar marcador en user turn correcto. `AMBIGUOUS` implica reconciliación read-only; un timeout RPC no demuestra que no hubo click. Los follow-ups no heredan la obligación de draft vacío ni de adjuntar un plan.

### 5.4 Startup, RPC y diagnósticos

Envolver bootstrap, auto-start de dependencias, policy inicial y loop en frontera común de error tipado, checkpoint y cleanup. No silenciar fallos con rc=0; preservar traceback técnico y estado accionable. Clasificar `INTERNAL_DEFECT`, `EXTERNAL_DEPENDENCY`, `RECONCILIATION_REQUIRED` y `RETRYABLE`.

RPC debe reconocer expiración/cancelación antes de efectos, propagar request ID/epoch y drenar respuestas tardías sin asignarlas a otra llamada. No encolar otro Send mientras el anterior tenga resultado incierto. Shutdown con espera limitada, cierre de pipes y terminate/kill del proceso propio; limpiar también el `proc` local si no alcanza broker_ready. Nunca bloquear indefinidamente en `readline` ni matar OpenCode/Chrome ajenos.

Timeline debe guardarse en **todas** las salidas de ensurePolicy, no solo la última guarda; `diag` serializa trace, predicado pendiente, tiempos, controles y errores sin secretos. Si falla screenshot, conservar JSON y explicar evidencia faltante. Fuente instalada y hashes se incluyen en el reporte del error.

## 6. Contratos para que el resto del loop termine

### 6.1 Dos modos de aceptación sin contradicción

| Modo nuevo | Escritura | Cierre válido | Lo que prueba |
|---|---|---|---|
| `read_only_probe` | Prohibidas mutaciones repo/CI/VPS/producción | `READONLY_CANARY_PASS` con obligaciones de herramientas cumplidas | Transporte y observación reales; no implementación ni nuevo CI. |
| `implementation` | Escritor autorizado del Chat publica cambio de alcance definido; operator no commit/push | `IMPLEMENTATION_GO` / DONE con candidato nuevo y CI exacto | Ciclo de ingeniería real, incluido writer. |

`run_kind` inmutable al crear run. **Los states legacy no tienen default de modo.** Antes de seleccionar prompts, despachar acciones o permitir efectos nuevos, una migración en modo de inspección verifica state, plan original y hash, outbox/acciones pendientes y evidencia del propósito. Solo adopta `implementation` si ese alcance está demostrado. Un plan legacy read-only conserva esa intención mediante migración compatible o se archiva como intento no aceptado y se lanza el probe nuevo después de reconciliar lo pendiente; jamás recibe el prompt commit/push durante esa decisión. Evidencia ausente, contradictoria o ambigua produce `RECONCILIATION_REQUIRED`, sin nuevos envíos ni escrituras funcionales. Si hubo un efecto SENDING/RUNNING, primero se reconcilia; no se reclasifica para ocultarlo. Registrar decisión, evidencia y schema antes de habilitar el dispatcher.

Prompts por modo. `read_only_probe` pide un evento propio (`PROBE_COMPLETE`), registra SHA baseline como **observado** y comprueba las restricciones funcionales; jamás lo convierte en candidato nuevo ni escribe `go_confirmed` de implementación. La clasificación y FSM admiten ese evento solo en ese modo, tras todas las obligaciones. El bootstrap read-only no usa el prompt “unique commit push”.

Read-only prohíbe **cambios funcionales** en repo, CI, datos, servicios y configuración VPS; permite logs, uploads/evidencia y receipts operacionales del control plane en directorios privados declarados por manifest. En el probe, los receipts del wrapper se guardan localmente: no autorizar escrituras remotas nuevas por llamarles auditoría. Si otro modo requiere receipts remotos, su directorio y permiso deben estar explícitamente autorizados; `/tmp/log` sigue protegido. La política se impone por código antes de cada acción y por operaciones read-only de adapters, además del prompt. Rechazar comandos mutadores o no clasificables, aunque los pida el chat. Auditar las operaciones ejecutadas y sus targets; snapshots SHA/hostname corroboran contexto, pero no prueban por sí solos ausencia de toda mutación del VPS.

El canary de implementación usa una tarea inocua acotada en repo/rama/CI de aceptación aislados; después se ejecuta el objetivo real `Trochez/bot_trading:feature/GRU`. Validar qué despliegues dispara cada push. No provocar fallos deliberados ni trades en producción. Conservar un commit consolidado **por iteración**, no un commit para todas las iteraciones de una recuperación.

### 6.2 Respuestas, bloque de acción y OpenCode

Observar sin recarga, conservar texto exacto/line breaks y hash, y comprobar finalización estable con dos snapshots/ventana configurable y señales activas del turno. No detectar rate limit/GO por texto histórico del body. Enumerar un bloque canónico por `pre`, eliminando la duplicación `pre` + `code`; materializar mismo message_id/block_id/hash/bytes, rechazando cambios de turno. OpenCode elige intención/metadatos, no retranscribe comandos.

Preflight semántico ejecuta una clasificación mínima por **la misma ruta CLI, agente, modelo y configuración** de producción y valida schema/vínculo. Separar `HTTP_HEALTHY` de `SEMANTIC_READY`. Alinear nombre y contenido del agente text-only; verificar herramientas/permissions efectivos. Si el servidor está sano pero CLI/modelo/agente no funcionan, bloquear antes del primer Send. Mantener proveedor/modelo existentes salvo cambio solicitado; no gastar llamadas para observar DOM que puede leer el broker.

### 6.3 Outbox, acciones y espera CI

Diagnosis/replan/procede/capabilities/evidencia usan outbox durable: `PREPARED → SENDING → SENT` o `AMBIGUOUS`. Fingerprint reserva la operación, pero no la considera entregada antes de `SENT/ALREADY_SENT`. Los stages `DIAGNOSIS_SENT`/`REPLAN_SENT` avanzan después de prueba; en restart se reconcilia la operación reservada. No esperar una respuesta a un delivery inexistente ni generar un delivery_id nuevo para reintentar el mismo efecto.

Acciones: receipt vinculado a run/iteración/action ID/target/command hash/execution ID y estados preparados/ejecutando/finalizados/entregados. Persistir intención antes de ejecutar; ejecutor local/VPS conserva resultado consultable incluso si cae controller. Si se desconoce si una acción con efectos se ejecutó, marcar `RESULT_UNKNOWN` y reconciliar; no prometer exactly-once para shell arbitrario. Replay automático solo si read-only comprobado o idempotente con clave/protocolo. Un timeout SSH no garantiza cancelación remota.

WAIT_CI necesita un scheduler cooperativo: consultar CI con su cadencia y atender nuevas respuestas/acciones autorizadas sin bloquearse en `continue` prolongado. No enviar follow-ups repetidos mientras CI sigue corriendo. Separar deadline de CI de deadline de mensajes/acciones. Un HEAD externo nuevo o rerun cambia la evidencia exigida, no se adopta ciegamente.

### 6.4 CI, Semaphore, artefactos y GO

Schema CI obligatorio: repo/rama/candidate SHA/provider/proyecto/run/pipeline/attempt, jobs/checks requeridos, estado/conclusión, timestamps y fuente observable. Rechazar rc no cero aunque haya JSON; SHA ausente/distinto, colección vacía, UNKNOWN, skipped/cancelled, intento viejo y jobs parciales no son SUCCESS. Consultar todos los checks obligatorios, paginación y política de proveedor configurada.

Semaphore: obtener identidad y resultado del pipeline/job concreto, no body global ni eco de args. Recoger failed_jobs con block/job/step/exit/log y origen; manejar SHA abreviado con resolución canónica demostrable, no substring. Auth legítima puede requerir acceso humano, sin bypass. Reproducción local solo con checkout exacto y aislamiento de credenciales/servicios; una allowlist textual `pytest` no limita lo que ejecuta el test. Distinguir `COLLECTION_COMPLETE`, `REPRODUCED`, `VALIDATION_PASSED` y `NOT_REPRODUCIBLE`; reportar por qué una reproducción no aplica, sin inventar PASS de tests.

Replan: corregir regex corrupto y probar enlaces `.md`, blob/data/download y forma de enlace ofrecida por Chat. Descargar bytes reales del mensaje correcto; UTF-8, tamaño/hash, contenido/estructura, ruta segura y escritura atómica. Rechazar HTML/login, archivo viejo, vacío y parcial. Si falta artefacto pedir corrección una vez por mensaje y continuar al nuevo; nunca fabricar bytes desde la paráfrasis del LLM.

GO exige evento del turno correcto después de revisión final, repo/rama/candidato atribuibles, HEAD antes/después de consulta CI coincidente, CI exacto vigente, obligaciones/acciones/outbox completas y despliegue verificado si lo requiere la tarea. Evidencia por run; alias global no puede cerrar otro run. Registrar intervalo observado: se acredita ese candidato en ese momento, no congelación futura de la rama.

## 7. Ubuntu Server con checkout local: contrato operacional

**No asumir WSL, `/mnt/d`, escritorio, usuario root ni credenciales preinstaladas.** El equipo ya tiene el repo local; lo descubre y trabaja allí, sin pedir al usuario que vuelva a clonarlo. Control plane y target son repos distintos.

Configuración nueva propuesta, a implementar y validar, no se afirma que el parser actual la soporte:

```yaml
schema_version: 1
control_repo_dir: /ruta/real/ai-control-plane
repo: Trochez/bot_trading
branch: feature/GRU
repo_dir: /ruta/real/bot_trading
chatgpt:
  project_url: <URL exacta configurada>
browser:
  mode: headed_display # o headless, probado explícitamente
  profile_dir: /ruta/privada/del/usuario/runtime
runtime:
  user: <usuario operativo existente>
integrations:
  ci_status: /ruta/absoluta/ci-status
  vps_wrapper: /ruta/absoluta/vps-ssh
```

Una sola fuente efectiva y precedencia documentada config/env/CLI. Validar claves/tipos, paths absolutos, accesibilidad, remote Git, rama y cwd de cada acción; cargar configuración antes de construir constantes. No crear directorios WSL como fallback. Installer preserva valores del usuario y secretos; migración a defaults solo si falta la clave, con reporte.

Browser: elegir modo explícito compatible. Para headed en servidor sin escritorio, habilitar display virtual/acceso visual privado administrado por el equipo, con un único owner y mismo usuario/perfil; para headless, probar sesión, upload/download y controles reales en ese modo. No asumir headless equivale a la sesión headed, no añadir `--no-sandbox` ni ocultación adicional para eludir restricciones. Autenticación se establece legítimamente en el perfil operativo y se reutiliza; login/MFA/CAPTCHA se reporta como dependencia cuando corresponda. No copiar cookies de otra persona ni publicar perfiles.

Validar Python, Node, Playwright y browser instalados y compatibles, librerías Ubuntu necesarias, espacio/permisos, certificados, reloj, DNS/red hacia dependencias, perfil y locks. Usar versiones fijadas en manifest de runtime, no actualizar todo a latest. Wrapper VPS/ci-status son dependencias explícitas: reutilizar implementaciones existentes validadas o implementarlas con contratos/config, sin placeholders que devuelvan PASS.

Preflight por modo comprueba: repo/path/branch; Chrome/display/perfil; acceso al proyecto; OpenCode real; GitHub read-only; VPS read-only; CI-status y Semaphore; plan legible; ausencia de owner conflictivo. Escritor Chat se descubre antes del canary y se demuestra con commit real durante aceptación; conexión GitHub no prueba permiso de escritura. Proteger tokens en logs y evidencias.

Startup debe invocar preflight o consumir su receipt vigente ligado a config/release/modo; no enviar el primer prompt para descubrir después que faltan adapters. Si hay servicio systemd existente, integrar su usuario/env/stop/start; si no, mantener supervisión existente o añadir una unidad específica probada. Evitar bucles automáticos de restart ante envíos ambiguos. Instalar como operación privilegiada separada de la ejecución cotidiana no root.

## 8. Backlog atómico, asignado y verificable

Cada tarea tiene **dueño, revisor independiente, dependencias y salida verificable**. `A01–A05` expresa todas las tareas de ese intervalo. Ninguna tarea se cierra por un print PASS sin oráculo. Se permite `VERIFIED_EXISTING` con prueba efectiva; no omitir gates. Los defectos adicionales se registran `DEF-xxx` con tarea/test/dueño y deben cerrarse antes de aceptación.

### M0 — Evidencia y contratos

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A01 | TL / AU | — | Identificar raíz Git/rama/HEAD/dirty/AGENTS del checkout local; comparar paquete/runtime, preservar trabajo ajeno y fijar fuente base. |
| A02 | SR / QA | A01 | Recoger JSON/HTML/PNG/log/state/ledger del incidente exacto y manifest privado saneado; ausencias declaradas. |
| A03 | QA / AU | A01,A02 | Incorporar reproducciones F01/F03/F04/F08 a tests de comportamiento; roja en base, salida esperada documentada. |
| A04 | TL / AU | A01 | Aprobar schemas de readiness/binding/outbox/receipt/CI y modos read-only/implementation, con ejemplos válidos e inválidos. |
| A05 | IN / TL | A01,A04 | Inventariar adapters, permisos y writer Chat; estados DISCOVERED/FEASIBLE/LIVE_PROVEN sin inventar disponibilidad. |

### M1 — Readiness, composer y envío

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A06 | BR / QA | A03,A04 | Sustituir espera truthy por transiciones de readiness y deadline monotónico compartido; T01 verde. |
| A07 | BR / QA | A06 | Resolver switcher por rol/nombre accesible scoped y unicidad; Chat/aria duplicados y Work→Chat cubiertos (T02). |
| A08 | BR / QA | A07 | Esperar trigger, menú, opción y selección persistente de reasoning; tipos de modelProof explícitos (T03). |
| A09 | BR / AU | A08 | Persistir timeline y diagnóstico completo de todos los errores/readiness; probar timeout y falta de captura (T04). |
| A10 | BR / QA | A04 | Exigir composer activo/present/raíz demostrada en fresh y resume; T05 rechaza `none`/otro composer. |
| A11 | BR / QA | A10 | Unificar localizadores de editor/adjuntos/send sobre esa raíz; eliminaciones solo de la transacción propia (T05–T06). |
| A12 | BR / CT | A11,A04 | Implementar upload transaccional y reconciliación con ledger durable del controller; estado uploading bloquea ALREADY (T06). |
| A13 | BR / AU | A08,A12 | Revalidar payload/policy/adjunto/contexto dentro de Send y click único; T07 y fallos entre pasos. |
| A14 | CT / BR | A13 | Enlazar pruebas/milestones al run/chat/epoch y reanudar desde observación válida, no repetir todos los pasos (T08). |

### M2 — Observación, durabilidad y RPC

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A15 | CT / SR | A04 | Frontera de error startup+loop, checkpoint tipado y rc no cero; error interno no termina como única evidencia traceback (T11). |
| A16 | CT / QA | A04 | Separar project_url de conversation binding y completar identidad tras Send/ruta genérica; T08 evita adoptar otro chat. |
| A17 | CT / BR | A16 | Quitar goto incondicional en observe/send; navegar solo por necesidad probada, preservando generación (T08–T09). |
| A18 | BR / QA | A17 | Observer de turno estable con texto exacto y señales activas scoped; no confundir hidden stop/rate text histórico (T09). |
| A19 | BR / IN | A18 | Bloques canónicos únicos vinculados a mensaje/hash/bytes; materialización rechaza DOM cambiado (T10). |
| A20 | CT / SR | A04,A15 | Hacer RPC/shutdown acotados, expirar operaciones y reconciliar respuestas tardías; limpiar proceso de arranque fallido (T12). |
| A21 | CT / QA | A14,A15 | Outbox durable para diagnóstico/replan/follow-up/evidencia y etapas solo tras entrega; T13 cubre fallos antes/después del click. |
| A22 | CT / AU | A04,A21 | Ledger de acciones/receipts preparado antes del efecto, recuperación de resultados huérfanos y RESULT_UNKNOWN (T14). |
| A23 | IN / CT | A22 | Receipt consultable de ejecutores local/VPS, timeout remoto y política por clase de efecto; T14 sin replay inseguro. |
| A24 | BR / QA | A03,A18 | Corregir regex U+0008 y adquisición real de archivos del turno actual en cada mecanismo soportado (T15). |
| A25 | CT / IN | A24 | Validar artefacto/provenance/hash/estructura y handoff atómico antes de nueva iteración (T15,T24). |

### M3 — Modos, herramientas y cierre

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A26 | CT / AU | A04,A21 | Implementar modos/eventos y migración legacy sin default, previa a todo dispatcher; enforcement read-only y obligaciones, sin candidato/GO falsos (T16). |
| A27 | IN / TL | A26 | Seleccionar prompts solo después de migración probada; bloquear legacy ambiguo y commit-push en read-only; un commit por iteración real (T17). |
| A28 | IN / QA | A05 | Alinear agente text-only y probar clasificación real de la ruta CLI/modelo/agente; separar health de capability (T18). |
| A29 | IN / AU | A04,A05 | Implementar contrato CI exacto, rc/schema, jobs requeridos e intentos vigentes; missing no es SUCCESS (T19). |
| A30 | CT / AU | A29,A22 | Endurecer candidato/FINAL_REVIEW/GO con identidad, pendientes, evidencia y HEAD antes/después (T20). |
| A31 | IN / BR | A29 | Recoger pipeline/job/step/log Semaphore scoped y SHA observado, sin body-global ni eco de args (T21). |
| A32 | IN / QA | A31 | Reproducción aislada del SHA y estados honestos de colección/reproducibilidad; no PASS de validación vacía (T22). |
| A33 | CT / QA | A21,A28,A29 | Scheduler WAIT_CI atiende mensajes/acciones autorizadas y deadlines sin spam ni adoptar otro candidato (T23). |
| A34 | CT / IN | A25,A27,A30–A33 | Completar transición fallo→evidencia→diagnóstico→replan→nuevo chat y nueva baseline/iteración (T24). |
| A35 | IN / AU | A05,A27 | Integrar contrato de writer autorizado en Chat; probar capacidades y denegación sin dar commit/push al operator (T25). |
| A36 | IN / QA | A23,A29 | Verificador de despliegue/health ligado al candidato cuando el plan lo exige; canaries VPS read-only (T26). |

### M4 — Ubuntu y empaquetado reproducible

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A37 | SR / CT | A04 | Parser de rutas/config real, precedencia y env antes de constantes; funcionar sin `/mnt/d` y preservar upgrade (T27). |
| A38 | SR / BR | A37 | Browser mode/display/perfil/UID explícitos y ownership único; headed/headless elegido se verifica (T28). |
| A39 | SR / IN | A05,A37 | Resolver provisión/validación real de ci-status y vps-ssh; dependencias/versiones fijadas, sin mocks operacionales (T29). |
| A40 | SR / QA | A28,A35,A38,A39 | Preflight de capacidades por modo integrado a start, con receipt/hash/frescura e informe de faltantes (T30). |
| A41 | SR / CT | A15,A20,A37 | Stop/restart/supervisión por PID/lock propio; no matar procesos de otra sesión ni auto-reintentar ambiguos (T31). |
| A42 | SR / AU | A26,A37–A41 | Instalar bundle coherente; migrar state/modo en staging antes de habilitar efectos; preservar config y rollback compatible (T16–T17,T32). |
| A43 | SR / QA | A42 | Generar manifest actual sin artefactos viejos/pycache; verificar clean extraction y trazabilidad fuente-runtime (T33). |
| A44 | TL / AU | A04,A27 | Publicar alcance seguro/manifests de escenarios: read-only, writer/CI aislado, recovery y target real; cero trading experimental. |

### M5 — Pruebas ejecutables e integración

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A45 | QA / BR | A03,A06–A13 | Servir fixture de app con DOM/hidratación/composer/menus/eventos reales; ejecutar broker real y regresiones (T01–T10). |
| A46 | QA / CT | A20–A36,A45 | Runner controller+broker reales con dobles solo externos; ejecutar ambas modalidades y recovery end-to-end (T34). |
| A47 | QA / AU | A46 | Fault injection en fronteras de upload/Send/outbox/acciones/CI/handoff; contadores independientes de efectos (T35). |
| A48 | QA / AU | A47 | Campaña de 100 loops sintéticos completos con seeds/manifests, oráculos y cero false GO/duplicados (T36). |
| A49 | AU / TL | A45–A48 | Auditar que tests llaman código real, fixture no predetermina PASS y observabilidad vincula eventos a pruebas (T37). |
| A50 | SR / QA | A42,A43,A49 | Ensayar instalación/upgrade/rollback en Ubuntu de prueba con paths no WSL y usuario final (T27–T33). |
| A51 | TL / AU | A48–A50 | Integrar revisión candidata, cerrar P0/P1 y ejecutar suite offline completa de esa revisión; congelar hash. |
| A52 | SR / AU | A51 | Instalar bundle candidato en servidor operativo; comparar hashes y preflight real sin enviar (T38). |
| A53 | BR / QA | A52 | Readiness live no-send de chat nuevo y conversación reanudada, sin borrar draft/estado del incidente (T38). |

### M6 — Aceptación live y entrega

| ID | Dueño / revisor | Depende de | Tarea y criterio de cierre |
|---|---|---|---|
| A54 | IN / AU | A44,A53 | Ejecutar canary read-only real con local/GitHub/VPS/Semaphore y ≥3 round-trips; `READONLY_CANARY_PASS` (T39). |
| A55 | IN / AU | A54 | Ejecutar implementación aislada por writer Chat, con un único upload/transacción del plan por iteración; ligar hash/bytes a run–chat–delivery y marker de user turn, demostrar respuesta estable, commit nuevo, CI real y GO independiente. Su ausencia, ambigüedad o segundo upload/send bloquea (T40). |
| A56 | IN / AU | A55 | Ejecutar CI failure controlado aislado: logs, diagnóstico, plan `.md` descargado y adjuntado exactamente una vez en el nuevo chat/iteración, nueva delivery/marker/respuesta estable, segunda implementación hasta GO. Persistir receipts; cualquier duplicado, pérdida o vínculo ambiguo bloquea (T41). |
| A57 | CT / AU | A55 | Reiniciar live después de Send y después de probe read-only; reconciliar mismo run hasta cierre, sin duplicados (T42). |
| A58 | TL / AU | A56,A57 | Ejecutar plan real en target `feature/GRU`; reanudar run original si es válido o iniciar nuevo si corresponde, hasta GO (T43). |
| A59 | AU / TL | A58 | Verificador independiente de evidence pack, hashes y todos los gates; emitir `FULL_LOOP_ACCEPTED` o incompleto (T44). |
| A60 | SR / AU | A59 | Entregar release/report/runbook/rollback/manifests/canaries/evidencias y matriz de cierre; ningún bug interno abierto. |

Paralelismo: después de A04, BR aborda M1, CT estado/RPC, IN capacidades/CI, SR portabilidad y QA fixtures; AU revisa contratos/evidencia. TL serializa cambios en daemon/broker y freezes. Live es serial para cada perfil/target. Factibilidad del writer y adapters se investiga en A05, temprano; no esperar al último gate para descubrir que faltan herramientas.

### Cobertura de hallazgos y del plan anterior

| Hallazgos / requisitos previos | Tareas de cierre |
|---|---|
| F01/F03/F20; WS4/WS13 hydration/diagnostics | A03,A06–A09,A45 |
| F04/F05; WS1–WS3/WS5/WS6 composer/upload/draft/Send | A10–A14,A21,A47 |
| F02/F06/F07/F19; WS7/WS8/WS12 observer/transport/restart | A15–A20,A22–A23,A41,A47,A57 |
| F08/F15; WS10/WS11 evidence/replan/artifact | A21,A24–A25,A34,A56 |
| F09; WS16/WS17 live canary/target | A26–A27,A44,A54–A59 |
| F10/F11; WS15/WS18 Ubuntu/install | A37–A43,A50–A53,A60 |
| F12/F13/F16; WS9/WS11 adapters/CI | A29–A33,A36,A46,A55–A56 |
| F14/F17; WS8/WS9 actions/semantic | A19,A22–A23,A28,A35 |
| F18; WS0/WS14/WS18 evidence/harness/release | A01–A04,A43,A45–A51,A59 |

Los 187 ítems previos no se consideran cumplidos por tener un binario llamado 4.4. Esta matriz consolida su alcance en unidades verificables y corrige la contradicción de aceptación read-only. No obliga a reescribir funciones que ya pasen sus contratos.

## 9. Matriz obligatoria de pruebas

Tests de verdad sobre funciones/procesos reales; no fuentes copiadas ni stubs de la función bajo prueba. Stubs solo para dependencias externas, con comportamiento, fallos y contador de efectos. La suite vieja queda como regresión auxiliar, sin otorgarle categoría E2E. Todos los Txx requieren comando, rc, versión/hash del código, salida/oráculo y evidencia. No hay `skip` silencioso de requisitos.

**Separación de niveles:** T01–T37 son pruebas offline/aisladas; auth, sesiones y fallos externos se representan con fixtures o adapters controlados. T28/T30 prueban los contratos de modo/perfil/preflight en ese entorno, no acreditan sesión autenticada del usuario. La comprobación autenticada real ocurre en G2/T38 y las operaciones externas en T39–T43; conservar resultados separados, sin etiquetar el fixture como LIVE_PROVEN.

### 9.1 Browser y runtime

| Test | Escenarios | Oráculo |
|---|---|---|
| T01 | Chat ausente en primera lectura, aparece a 100 ms/2 s/dentro del presupuesto; nunca aparece | No timeout prematuro; observa más de una vez; nunca presente agota deadline explicado, cero Send. |
| T02 | Work→Chat, texto/aria duplicados, idioma/layout observado, múltiples controles, click sin listener todavía | Control único scoped; se prueba estado tras acción; no falsa coincidencia ni click histórico. |
| T03 | Reasoning trigger/menú/High tardíos, disabled, cambio que resetea selección, modelo desconocido | Espera condición dentro del presupuesto; policy completa o bloqueo; no downgrade. |
| T04 | Error en cada etapa, timeout, screenshot falla, timeline tardía | Timeline/evento/predicado/elapsed persistidos en todas las salidas; secretos ausentes. |
| T05 | Composer `none`/unproven, visible equivocado, TARGET vacío con archivo/texto previo, histórico | Fresh solo con raíz activa y limpio; resume adopta únicamente transacción propia. |
| T06 | Tres file inputs, upload lento, input se limpia, retry, dos chips, sufijo nombre, error, otro composer | Exactamente un upload propio y un adjunto válido; no eliminación global; uploading no es ALREADY. |
| T07 | Policy/proyecto/archivo/texto/epoch cambian entre prueba y click, marker de otro chat | Send bloqueado; botón dentro de composer activo; un click ante contexto íntegro. |
| T08 | Same URL, URL genérica→canónica tardía, restart con chat enlazado, pestaña ajena | Observe sin goto redundante; mismo run/chat; pruebas viejas invalidadas y reconciliadas. |
| T09 | Respuesta parcial, hidden stop, tool activity, rate-limit citado en historial, multiline | SETTLED solo del turno correcto y estable; texto exacto; cero mensajes durante generación. |
| T10 | `pre > code`, varios bloques, mismo texto repetido, mensaje cambia antes de extraer | Cada bloque una vez, ID/hash/bytes congruentes; cambio rechaza, no ejecución aproximada. |
| T11 | Policy startup falla; auth expiró; error interno y terminal; SIGTERM | Estado/error tipado y rc correcto; no éxito por catch; cleanup propio y resume consistente. |
| T12 | Broker sin ready, pipe sin newline, RPC expirado, respuesta tardía, shutdown colgado | Tiempo acotado; no huérfanos propios; no side effect tardío sin reconciliar; lock no liberado prematuramente. |

### 9.2 Durabilidad, FSM e integraciones

| Test | Escenarios | Oráculo |
|---|---|---|
| T13 | Crash/fallo pre-Send, post-click y post-confirmación en diagnosis/replan/procede/evidencia | Outbox recuperable, stage solo tras SENT; mensaje no perdido y no duplicado. |
| T14 | Acción termina antes de guardar resultado/state; resultado huérfano; timeout local/VPS | Receipt original recuperado; contador de efecto ≤1 para caso no idempotente del harness; desconocido bloquea, no replay ciego. |
| T15 | `.md` sin palabra download, links blob/data/evento, parcial/login/HTML/UTF-8 inválido/viejo/path traversal | Descarga real correcta o rechazo; no U+0008; hash/estructura/origen verificados. |
| T16 | Read-only sin candidate; petición mutadora; GO prematuro; legacy sin run_kind con plan read-only/prompt commit, implementation probado o propósito ambiguo | Enforcement rechaza mutación antes de ejecutar; migración preserva intención, solo implementation demostrado se habilita; ambiguo se reconcilia sin efectos. Probe nunca produce GO de implementación. |
| T17 | Selección de prompts después de migración legacy; plan ausente/hash contradictorio; prompts por repo y dos iteraciones | Legacy read-only nunca recibe commit/push; ambiguo no selecciona/envía prompt operativo; implementation probado usa contrato correcto; un commit por iteración. |
| T18 | HTTP OpenCode OK pero agente/modelo/CLI inválido; tool permissions erróneos; JSON inválido | Health no equivale a semantic PASS; schema/ruta real validados; browser tools no disponibles al intérprete. |
| T19 | CI rc!=0 con JSON, sha vacío/otro, checks vacíos/parciales, UNKNOWN, cancel/skip, intento anterior, paginación | Ningún caso inválido SUCCESS; colección completa del candidato e intento requeridos. |
| T20 | Commit ajeno concurrente, GO de otro mensaje, pendientes, HEAD cambia durante final review | Candidato atribuible; evidencia de revisión correcta; rechazo de falso GO. |
| T21 | Semaphore dashboard con varios pipelines, abreviado, auth, job details y logs grandes | Identidad derivada de pipeline concreto; failed_jobs/step/logs reales, sin eco de args. |
| T22 | Repro exacto, sin comando seguro, comando de test con efecto externo, dependencias faltantes | Aislamiento; reproducibilidad separada de colección; no PASS de tests no ejecutados. |
| T23 | CI RUNNING mientras aparece action request; CI UNKNOWN prolongado y respuesta larga | Scheduler atiende acción autorizada sin spam; deadlines independientes y candidato intacto. |
| T24 | Failure→evidence→diagnosis→plan ausente→archivo real→nuevo chat→nuevo candidato→GO | Handoff/iteración/parent/baseline correctos; una operación lógica por entrega confirmada. |
| T25 | Writer Chat accesible/no disponible; intento operator commit/push | Writer se prueba donde corresponde; operator sigue bloqueado; ausencia real no se tapa con Work. |
| T26 | CI verde con deploy requerido ausente/otro SHA/salud fallida | Sin GO hasta receipt operacional exacto; si no requiere deploy, queda explícito en manifest. |

### 9.3 Ubuntu, integración completa y aceptación

| Test | Escenarios | Oráculo |
|---|---|---|
| T27 | Repo local bajo `/srv` o `/home`, sin `/mnt/d`; YAML/env/CLI y reinstall | Paths/cwd/remote/rama correctos; config no ignorada ni sobrescrita. |
| T28 | Ubuntu de prueba sin display, modo válido, perfil ocupado/UID equivocado y auth simulada vencida | Contratos offline distinguen causas y ownership; autenticación real se demuestra aparte en T38. |
| T29 | Falta ci-status/vps-ssh, no ejecutable, contrato roto, DNS/TLS/auth | Falla antes del Send con componente identificado; no falso PASS. |
| T30 | Preflight nuevo/resume, receipt viejo/config cambió y errores de credenciales simulados | Gate offline ligado a release/config/modo y sin secretos; probes autenticados reales se verifican en T38–T39. |
| T31 | Dos controllers, otra sesión OpenCode, stop/restart/SIGTERM/crash | Un owner por perfil/run; otros procesos sobreviven; mismo state reanudado. |
| T32 | Instalación parcial/migración fallida/downgrade incompatible/rollback tras efectos | Runtime coherente o anterior compatible; no restaurar ledger viejo que permita duplicados. |
| T33 | Manifest stale, byte modificado, tar limpio, versiones/nombres legacy | Todo artifact/runtime corresponde a fuente probada; clean extraction reproduce resultados. |
| T34 | Controller Python + broker Node + navegador real en app local + adapters simulados | Happy/recovery/read-only ejecutan FSM/transporte/acciones/CI/handoff/GO reales; no dict-only soak. |
| T35 | Matar procesos en cada frontera: upload, fill, Send, generation, receipt, evidence, CI, plan | Reconciliación demostrada por eventos/contadores independientes; ningún efecto duplicado ni mensaje perdido. |
| T36 | 100 escenarios E2E sintéticos recuperables, seeds fijas y delays/fallos controlados | 100 terminales esperados: GO en implementation y READONLY_CANARY_PASS en probe; cero duplicados/falso GO. Casos terminales negativos van aparte y deben bloquear. |
| T37 | Auditoría de eventos + ausencia/adulteración de evidencia/test; guardas desactivadas en copia de prueba | Verificador detecta defectos; campos y vínculos obligatorios presentes; source-string no cuenta como comportamiento. |
| T38 | Runtime instalado y no-send live, fresh y resume, mismo modo browser/usuario final | Hashes iguales al candidato; políticas y contexto comprobados; cero nuevos user turns. |
| T39 | Probe read-only real: Chat, OpenCode, local, GitHub, VPS y Semaphore | ≥3 round-trips al mismo chat, receipts/evidencia completa, ningún cambio Git/CI/VPS; cierre propio. |
| T40 | Implementación mínima real aislada mediante writer Chat; plan adjunto, bytes/hash, delivery y user-turn marker; restart en upload/Send | Exactamente una transacción/upload del plan y un Send por iteración, ligados al mismo run/chat/delivery y a una respuesta estable; tras restart no hay segundo upload/send. Commit nuevo único, candidato/CI reales y GO independiente; operator no publica. |
| T41 | CI realmente fallido aislado y reparación sin intervención humana de continuidad; plan de recovery descargado, validado y adjuntado al nuevo chat/iteración; restart en handoff | Logs exactos, diagnóstico y plan `.md` físico con hash/origen, exactamente un upload y Send de la nueva iteración, marker/respuesta estable, parent/baseline correctos, CI verde y GO. Falta/ambigüedad/duplicado bloquea. |
| T42 | Dos restart live: después del click; tras probe local/VPS terminado | Mismo run/chat, receipt original, sin duplicados, termina el escenario; no crash de trading real. |
| T43 | Objetivo real en `Trochez/bot_trading:feature/GRU` | Implementación/candidato/CI/acciones requeridos completos; GO final fechado; deploy solo si es parte del alcance autorizado. |
| T44 | Evidence pack final y fixture con hash/test/CI alterados | Aceptación solo del conjunto íntegro y completo; no autorreferencia del manifest ni GO reutilizado. |

La nueva suite debe fallar cuando se reintroduzca F01 o se retire una guarda crítica en una **copia de prueba**. Así se demuestra que el test detecta la regresión. No mutar runtime live para esa comprobación.

## 10. Gates y protocolo de aceptación real

| Gate | Requisito | Responsable |
|---|---|---|
| G0 — Base/factibilidad | Fuente/runtime/evidencia identificados, contratos de modos y capacidades al menos FEASIBLE; desconocidos documentados | TL/IN, revisión AU |
| G1 — Offline funcional | T01–T37, suites heredadas aplicables y 100 recorridos reales del harness; cero P0/P1 abiertos | QA/AU |
| G2 — Ubuntu instalado | Instalación/upgrade/rollback, manifest íntegro, preflight y T38 no-send bajo usuario/modo finales | SR/BR/AU |
| G3 — Integraciones read-only | T39 completo, sin mutaciones y sin reclamar GO de implementación | IN/AU |
| G4 — Implementación/recuperación | T40–T42 completos con writer, CI real, artefactos y restart | TL/IN/CT/AU |
| G5 — Target/release | T43–T44, evidencia independiente, `FULL_LOOP_ACCEPTED` y entrega reproducible | TL/AU/SR |

`FEASIBLE` es descubrimiento de interfaces/permisos; `LIVE_PROVEN` exige la operación real. G0 no exige anticipadamente el commit que se hará en T40. El código de adapters del tar no prueba acceso a servicios del servidor.

### Escenario read-only

Plan propio por modo con nonce en cada acción: (1) rama/SHA/cwd local; (2) SHA remoto por GitHub read-only; (3) hostname/UTC/SHA del checkout remoto por wrapper; (4) pipeline/job histórico conocido por Semaphore, identificado y solo observado. Devolver evidencia literal al mismo chat en al menos tres turnos. Enforcement y audit trail de las operaciones prueban que el loop no solicitó mutaciones funcionales; snapshots antes/después corroboran identidades, commits y estado CI, sin afirmar ausencia de escrituras de todo el sistema operativo. Receipts/evidencia autorizados se conservan en el control plane. El evento final `PROBE_COMPLETE` se valida contra obligaciones y receipts; no produce `go_confirmed` de implementación.

### Escenario de implementación

Manifest declara repo/rama/CI de aceptación y archivo/tarea mínima inocua. Inspeccionar triggers/deploys antes del push. Chat usa su escritor autorizado, crea un commit consolidado; operator solo ejecuta acciones permitidas y observa. Controller liga candidato al trabajo, espera jobs requeridos, solicita revisión y valida GO. La identidad del candidato se obtiene desde GitHub, no de la afirmación del chat.

### Escenario de CI failure y replan

En destino aislado, usar un test de aceptación determinista que falle por una condición corregible en el código. Pipeline real falla; obtener job/step/logs exactos. Entregar al mismo Chat; obtener diagnóstico y un plan físico con timestamp. Si los slash commands no están disponibles en esa superficie, suministrar las instrucciones efectivas del protocolo/skill; escribir `/ralplan` no demuestra por sí solo que se ejecutó. Descargar/validar archivo; nueva iteración/chat; escritor publica su segundo commit (uno por iteración), CI verde y GO. No falsificar JSON CI ni cambiar states manualmente para recorrer la rama.

### Escenario de reinicio y objetivo real

Fault injection live solo en el run de aceptación y acciones inocuas; tocar PID/grupo propio. Reanudar mediante state existente, no `start` de otro run. Para el incidente original, inspeccionar deliveries/acciones/CI y hash de plan antes de decidir. Si el plan original es read-only incompatible, no cambiarle modo silenciosamente: cerrar como intento no aceptado y ejecutar el probe nuevo, conservando evidencia y sin duplicar efectos; ejecutar aparte la implementación completa. Si es implementation válido, migrar/reconciliar y continuar el mismo run.

Después ejecutar el plan objetivo real; el alcance de trading/deploy no se amplía por estas pruebas. El equipo trabaja autónomamente en los bugs y repite el gate afectado. Reiniciar desde cero solo en nuevos escenarios de prueba después de reconciliar el anterior; nunca usar un nuevo run para evadir un Send ambiguo.

### Cero continuidad manual y convergencia

Desde el primer Send hasta el cierre de cada escenario, cero mensajes humanos `continúa/procede`, cero ediciones manuales de state/ledger, cero commits del operator y cero clicks manuales para disimular bugs. Login/MFA legítimos se resuelven antes; si irrumpen durante el ensayo, el escenario queda bloqueado y se repite/reanuda conforme al contrato después de restaurar acceso. Bloqueo no cuenta como PASS.

Ante bug interno: registrar defecto y evidencia, reproducir, corregir, repetir regresiones y gates afectados sobre el nuevo hash. Repetir G1 y G4 si cambia controller/broker/identidad/efectos; mantener un análisis explícito de impacto para cambios menores. Si una clase falla dos veces, TL+BR/CT+AU revisan diseño antes de seguir. La campaña continúa hasta cumplir; ningún presupuesto agotado autoriza declarar éxito. Los procesos individuales tienen deadlines y checkpoints, evitando gastar indefinidamente en el mismo fallo sin diagnóstico.

## 11. Pre-mortem deliberado

| Escenario | Señal temprana | Prevención y prueba | Recuperación/dueño |
|---|---|---|---|
| 1. El timeout cambia de nombre pero sigue ocurriendo antes de readiness | Una sola observación; falla antes del presupuesto; tests solo inspeccionan strings | Predicados por etapa, fixture con DOM tardío/click sin efecto, T01–T04 y regresión sobre base | BR corrige con timeline; QA exige roja/verde, sin aumentar sleep. |
| 2. Se arregla bootstrap pero el canary nunca termina | FINAL_GO ignorado sin candidato; prompt read-only pide commit | Modos explícitos y prompts coherentes; T16/T17; writer investigado temprano y probado live | CT/IN reparan protocolo; no fabricar candidate ni quitar CI. |
| 3. Reinicio duplica o pierde un efecto, o CI de otro run cierra GO | Outbox SENT sin marcador, receipt ausente, JSON SUCCESS sin identidad | Outbox/receipt, fault matrix T13/T14/T19/T20/T35/T42, verificador independiente | CT/AU reconcilian; desconocido bloquea, jamás replay/GO ciego. |

Tradeoff real: más prueba de identidad y durabilidad puede bloquear cuando UI/servicios no entregan datos completos. La solución es adquisición y diagnóstico mejores, no aceptar UNKNOWN como PASS. Cambios pequeños más pruebas completas reducen el riesgo de reescritura innecesaria.

## 12. Evidencia y observabilidad exigidas

Por evento: run/iteración/run_kind, phase/subphase, chat/page/project binding, request/delivery/action ID, epoch, UTC y elapsed monotónico, hash release/config/policy, predicado esperado, resultado y enlace/hash de evidencia. Timeline acotada por transiciones, no volcado ilimitado del DOM. Logs legibles deben decir qué falta, presupuesto restante y checkpoint de recuperación.

Paquete final:

1. `release-manifest.json`: source Git SHA/tree cuando exista, hash del tar, runtime/dependencias/config efectiva saneada, hashes de todos los componentes.
2. `test-results.json`/JUnit: Txx, comando exacto, rc, tiempos, versiones, seed y oracle; fallos previos conservados.
3. `acceptance-manifest.json`: run_kind, chats/deliveries/actions/receipts, por cada iteración el único plan upload/transacción (bytes/hash, chat, delivery ID y user-turn marker), respuesta estable y cualquier restart/reconciliación; candidate/baseline, CI/provider/run/pipeline/attempt/jobs, artefactos y GO/probe receipt, todos por hash/ruta. La ausencia, duplicación o vínculo ambiguo invalida `IMPLEMENTATION_GO` y `FULL_LOOP_ACCEPTED`.
4. `IMPLEMENTATION_REPORT_<UTC>.md`: causas confirmadas, cambios, matriz Fxx/Axx/Txx, cobertura del plan previo, resultados y limitaciones.
5. Canaries reales `.md`, logs/JSON/traces/PNG saneados, plan de recovery descargado, runbook/install/rollback.

Verificador final lee manifest congelado y escribe dictamen separado con hash de entrada; un índice externo referencia ambos. Ningún archivo incluye su propio hash ni depende de un resultado que todavía no existe. T44 prueba aceptación y rechazo de evidencia adulterada. Mantener originales privados; redacciones declaradas y vinculadas al original, sin compartir credenciales/perfiles/cookies.

Métricas: tiempos de navegación/readiness/adjunto/Send/respuesta/acción/CI/recovery; recargas evitadas; retries, unknowns, duplicados detectados, GO rechazados. Los objetivos de rendimiento se calibran con el servidor real y no desplazan corrección; error instantáneo no es mejora de latencia. Señales PASS solo después de verificar su contrato, especialmente OpenCode, CI y soak.

## 13. Runbook para el equipo en Ubuntu Server

### 13.1 Descubrir el checkout y congelar evidencia

Ejecutar desde el checkout local que ya tiene el equipo. Estos comandos solo inspeccionan; no asumen la ruta WSL:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
rg --files -g AGENTS.md -g 'ai-loopd-v3.py' -g 'browser-broker-v1.cjs' -g '*verify*'
rg -n 'CHAT_SURFACE_HYDRATION_TIMEOUT|chat_policy_hydration|def ensure_chat_policy' ai-loop-v4.3
```

Si el checkout ya cambió, mapear los símbolos antes de editar; no forzar el hash del tar ni descartar cambios ajenos. Leer AGENTS aplicables del host aunque el tar no contenga ninguno. Copiar y hashear evidencia exacta bajo el run actual antes de tocar runtime; leer JSON → screenshot → HTML. Rutas del incidente:

```text
/var/lib/ai-loop/state/R20260922T160843.v3.json
/var/lib/ai-loop/logs/R20260922T160843.v3.log
/var/lib/ai-loop/runs/R20260922T160843/browser/broker-diagnostics/
  2026-09-23T001147974Z-ENSURE_CHAT_POLICY.{json,html,png}
  2026-09-23T001152437Z-ENSURE_CHAT_POLICY.{json,html,png}
```

### 13.2 Implementar, probar e instalar

No ejecutar `install.sh` antes de superar los tests del mismo bundle en staging. El script actual modifica runtime/config in situ y contiene rutas WSL; A37–A43 deben corregirlo. No usar `kill-all` genérico para detener sesiones no relacionadas. Coordinar stop del owner identificado y tomar backup de bundle/config/state con hashes.

Los comandos siguientes son **interfaces propuestas para v4.5**, a entregar realmente y documentar, no herramientas que ya existan:

```text
bin/verify-v4.5-local --manifest <test-config>
bin/doctor-v4.5 --config <config> --run-kind <modo> --no-send
bin/acceptance-v4.5 --scenario read-only|implementation|recovery|restart|target --manifest <config>
bin/verify-acceptance-v4.5 --manifest <acceptance-manifest.json>
```

Cada modo devuelve rc no cero por fallo/requisito faltante y resultado estructurado; prohibir force-go/skip-required. `doctor --no-send` nunca invoca una ruta que pueda enviar. Evidencia de cada ejecución se guarda por run/escenario.

Instalar release candidata con fuente/config identificadas, mantener entrypoints `start-loop-v3`, `restart-loop-v3` y state schema migrable. Rollback restaura componentes compatibles y conserva receipts posteriores; no restaurar ledger antiguo después de efectos nuevos. Una release final solo se empaqueta como aceptada después de G5, con los mismos bytes del candidato ensayado. Si cambia código luego del canary, repetir gates afectados antes de etiquetar release.

### 13.3 Reanudar el incidente sin duplicarlo

Tras migración y pruebas, si state/chat/plan/delivery del run son válidos, el entrypoint legacy documentado conserva identidad:

```bash
/opt/ai-loop/bin/restart-loop-v3 /var/lib/ai-loop/state/R20260922T160843.v3.json
tail -F /var/lib/ai-loop/logs/R20260922T160843.v3.log
```

Antes deben verificarse owner, config, modo y ledger. No ejecutarlo a ciegas por el solo hecho de que el error incluya “startup”: ese run puede haber enviado antes. Para un objetivo/escenario nuevo usar start con plan explícito después de reconciliar lo pendiente.

## 14. Handoff team → ralph

Se entrega planificación; no se ha invocado implementación en el servidor desde esta sesión. La skill no garantiza que `/team` o `/ralph` estén instalados: confirmar su existencia y, de faltar, conservar roles/protocolo con coordinador local y `task(subagent_type="general"|"explore", ...)`, sin inventar agentes o plugins.

Prompt sugerido desde el repo local del **control plane**, con este archivo adjunto:

```text
/team Implementa completamente este plan ai-loop v4.5 en el Ubuntu Server
con el checkout local existente. Equipo total 7: TL, BR, CT, IN, QA, SR, AU.
Verifica repo/rama/HEAD/AGENTS y conserva cambios ajenos. Repara los defectos
demostrados; no reimplementes funciones que pasen VERIFIED_EXISTING.
Completa A01-A60 y G0-G5; usa general/explore disponibles sin imponer modelos.
Corrige la espera truthy, los contratos read-only/implementation y los demás
hallazgos. Mantén Chat y operator sin commit/push. Ejecuta tests de comportamiento,
100 E2E sintéticos reales, canaries live, CI failure/replan y restart hasta GO.
No cierres al encontrar el siguiente bug: regístralo, reprodúcelo, corrígelo y
repite gates afectados. Entrega evidencia por SHA y dictamen independiente.
```

Team entrega revisión congelada/manifests/resultados; después AU dirige verificación **secuencial** tipo ralph, con TL para integración de correcciones:

```text
/ralph Verifica el plan adjunto v4.5 y sus manifests sobre la revisión exacta.
Audita Fxx→Axx→Txx, pureza read-only, writer real, CI/SHA/GO, receipts,
restart y recovery con plan descargado. Reproduce gates faltantes o invalidados.
No aceptes strings del source, 100 diccionarios, skips ni BLOCKED como éxito.
Devuelve defectos al dueño; después de corregir, revalida la nueva revisión.
Finaliza solo con FULL_LOOP_ACCEPTED demostrado o estado incompleto externo
con checkpoint y requisito concreto para reanudar, sin etiquetar release aceptada.
```

Alternativa ralph sin team: un implementador recorre carriles en orden de dependencias; especialistas `general` revisan puntos críticos y AU independiente valida al final. Reducir concurrencia no reduce gates. Razonamiento alto/máximo en browser/FSM/identidad/efectos y auditoría; medio/alto en empaquetado. Los modelos/proveedores existentes no se sustituyen por nombres prescritos por esta skill.

## 15. Definición de terminado y registro de consenso

Checklist obligatorio de implementación:

- [ ] F01 reproducido en base y corregido; el DOM real actual se documentó, sin confundir runs históricos.
- [ ] Todos F01–F20 cubiertos por tareas/tests; P0/P1 y defectos descubiertos cerrados.
- [ ] Config/rutas/display/UID/perfil/adapters funcionan en Ubuntu Server sin depender de `/mnt/d`.
- [ ] Tests T01–T44 y G0–G5 con evidencia; 100 E2E verdaderos, no contadores ficticios.
- [ ] Read-only cierra con obligaciones completas y no se presenta como implementación GO.
- [ ] Chat writer, OpenCode, local, GitHub, VPS, Semaphore, upload/download y múltiples turnos funcionan live; cada iteración tiene exactamente un plan upload/Send demostrado por receipt y marker, incluso tras restart.
- [ ] Recovery de CI con diagnóstico/plan físico y nueva iteración llega a GO.
- [ ] Restart/outbox/receipts evitan duplicados y mensajes perdidos; cero efecto ambiguo pendiente.
- [ ] Target real termina con HEAD/candidate/CI exactos, revisión final y deploy cuando aplique.
- [ ] Runtime/report/manifests corresponden a la misma release; auditor independiente acepta.

Estado final de campaña: `FULL_LOOP_ACCEPTED` o `INCOMPLETE_INTERNAL` / `BLOCKED_EXTERNAL`. Los dos últimos preservan evidencia y requieren continuar; no satisfacen el objetivo. No existe garantía de disponibilidad permanente de servicios externos, pero sí obligación de demostrar el resultado real antes de cerrar.

**Consenso de esta planificación:** Planner completó contexto y análisis del source; descubrimiento adicional realizado por un revisor explore. Ronda 1, secuencial: Arquitecto **ITERATE**, después Crítico **ITERATE**, ambos por el bloqueo de default implementation en states legacy read-only. Se corrigió §6.1 y su trazabilidad A26/A27/A42/T16/T17 para migrar antes de efectos, sin default y con reconciliación de ambiguos. También se incorporaron enforcement read-only/receipts, separación offline-live, procedencia de modelProof y la prueba live de un único plan upload/Send por iteración con marker, hash y restart en A55/A56/T40/T41/manifest. Ronda 2, secuencial: Arquitecto **APPROVE**; después Crítico **APPROVE**, sin hallazgos accionables. Esto aprueba la planificación, no acredita todavía el PASS live: la implementación debe completar G0–G5 y producir `FULL_LOOP_ACCEPTED`.

Presupuestos de consenso: variables `OMX_CONSENSUS_AGENT_TIMEOUT_MS`, `OMX_CONSENSUS_TOTAL_TIMEOUT_MS`, `OMX_CONSENSUS_MAX_REVIEW_ITERATIONS` y circuit breaker de la skill; si un experto no está disponible se documenta fallback local, sin inventar consulta. Son presupuestos de revisión, no autorización para omitir aceptación runtime.

## 16. Referencias y procedencia

- [D1] Tar adjunto y hash de §2.1; rutas/líneas de hallazgos corresponden a esa instantánea, no a una lectura de `/opt/ai-loop` remoto.
- [D2] Log/traceback actual del usuario; fija run, versión declarada, baseline y secuencia del fallo.
- [D3] `SKILL(6).md`, `omo-ralplan`; leído completo, fuente del proceso secuencial deliberativo.
- [D4] Plan v4.4 incluido en `plan_to_do`; contratos previos considerados y contrastados, no asumidos implementados.
- [E1] Ejecución local de `verify-v4.3-local` y reproducciones aisladas sobre código real, resultados resumidos en §2.4. No son aceptación live.
- [S1] [Playwright — Navigations / Hydration](https://playwright.dev/docs/navigations#hydration), consultado 2026-09-23: la acción puede preceder a listeners; se usa como apoyo de diseño, no como prueba del DOM del incidente.
- [S2] [Playwright — BrowserType / Persistent context](https://playwright.dev/docs/api/class-browsertype#browser-type-launch-persistent-context), consultado 2026-09-23: referencia para modo/contexto persistente y perfil; configuración efectiva se prueba en Ubuntu del equipo.

No se atribuye a documentación pública la disponibilidad de un modelo, writer, cuenta, permiso o sesión particulares: se prueba en la implementación bajo configuración autorizada.
