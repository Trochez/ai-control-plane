# Plan de implementación ai-loop v4.3: política de Chat verificable y ciclo completo hasta GO

Fecha de elaboración: **2026-09-22 03:09:06 -05:00 (Colombia)** / **2026-09-22 08:09:06Z**.  
Proyecto: `agentic_pipeline / ai-loop`. Base documental: `4.2.0`. Versión propuesta: `4.3.0`.  
Incidente: `R20260922T024027`, `MODEL_SOL_OPTION_NOT_FOUND`.  
Método: skill adjunta **omo-ralplan**, modo **deliberate**, no interactivo.  
Estado del documento: **APROBADO — Arquitecto APPROVE y Crítico APPROVE, ronda 1**.  
Estado de implementación y pruebas live: **NO EJECUTADAS en esta planificación**.

## 1. Objetivo obligatorio y contrato de terminación

Reparar el bootstrap y entregar una versión que complete, con evidencia real, el ciclo **plan → Chat del proyecto correcto → implementación → acciones locales/GitHub/VPS → devolución de evidencia → candidato Git → CI/Semaphore → revisión final → GO validado**. También debe completar la ruta **CI fallido → logs exactos → diagnóstico → replan descargable → nuevo chat → nueva implementación → CI exitoso → GO**.

La implementación no termina al desaparecer el traceback, al abrir el selector, al enviar el primer mensaje, al obtener selftests verdes ni al declarar un modelo que terminó. Termina cuando los gates de este documento están satisfechos y un verificador independiente valida la evidencia.

**Definición de éxito del producto:** `phase=DONE`, `go_confirmed` ligado al run/iteración y candidato actuales, `HEAD remoto == candidate_sha`, todos los checks/pipelines requeridos exitosos para ese SHA, ninguna acción o entrega pendiente/ambigua, y `FINAL_GO` explícito de la conversación correcta posterior a la evidencia de CI. Si la tarea exige despliegue, se exige además evidencia operacional del despliegue de ese candidato. Un bloqueo externo se reporta como `BLOCKED_EXTERNAL`, nunca como éxito.

**Definición de entrega de esta planificación:** un plan completo y revisado. No se promete que un plan pueda garantizar disponibilidad futura de ChatGPT, GitHub, Semaphore o VPS. Sí se obliga al equipo a ejecutar los ensayos reales antes de declarar `FULL_LOOP_ACCEPTED`.

## 2. Alcance, repositorios y evidencia disponible

### 2.1 Separar el producto reparado del repositorio operado

| Elemento | Identidad / función | Regla |
|---|---|---|
| Código a reparar | `/mnt/d/works/ai-control-plane/ai-loop-v4.2` en el checkout de `/mnt/d/works/ai-control-plane` | Inspeccionar raíz Git, rama, HEAD, cambios locales y AGENTS.md; no asumir que la rama es `feature/GRU`. |
| Runtime a actualizar | `/opt/ai-loop` | Instalar un bundle coherente; conservar entrypoints `*-v3` compatibles. |
| Estado/evidencia | `/var/lib/ai-loop` | Preservar runs, deliveries, acciones, hashes y archivos de diagnóstico. |
| Repo operado por el loop | `Trochez/bot_trading`, rama `feature/GRU` | Es el destino del trabajo funcional del chat, no el lugar donde insertar el controller. |
| Checkout operado | `/mnt/d/works/bot_trad/bot_trading` | Validar origen/rama/SHA antes de acciones o reproducción local. |
| Chat | Proyecto `bot_trading`, superficie `Chat` | No usar Work/Codex como recuperación automática. |

El `prompts/implement.txt` documentado contiene un destino fijo `feature/GRU`. **No entregar este plan de reparación al loop actual sin distinguir su repositorio de implementación**: podría ordenar cambios del control plane en el repo de trading. El equipo implementador trabaja primero en el control plane; después instala y ejecuta planes canary destinados explícitamente al repo de prueba/target correspondiente. Los prompts y manifests nuevos incluirán repo, rama y propósito por iteración.

### 2.2 Fuentes realmente inspeccionadas

1. Traceback pegado por el usuario.
2. `DOCUMENTACION_COMPLETA_AI_LOOP_V4_2_20260922T0155-0500.md`, especialmente §§6, 10–14, 20–28, 29–47, 49–64, 70–85 y 95–113.
3. `SKILL(4).md`: Planner → Architect → Critic secuenciales, ADR, pre-mortem, pruebas ampliadas, equipo y handoff team → ralph.
4. Referencias oficiales técnicas del §18, usadas únicamente como apoyo de diseño, no como evidencia del DOM del incidente.

No están disponibles en esta sesión el código instalado, el checkout del host, el JSON/HTML/PNG del fallo, las credenciales ni la sesión de Chrome del usuario. Se comprobó que esas rutas del host no existen en el entorno de planificación. No se ha reproducido el incidente live ni ejecutado la suite de ai-loop.

### 2.3 Hechos, hipótesis y cierre diagnóstico

Cadena observada:

```text
main() [ai-loopd-v3.py:4820]
  → start_new_chat() [ai-loopd-v3.py:4146]
  → CHATGPT_DETERMINISTIC_BOOTSTRAP_FAILED_NO_SEND
  → BROWSER_BROKER_ENSURE_CHAT_POLICY_FAILED
  → MODEL_SOL_OPTION_NOT_FOUND
```

Las líneas pertenecen al traceback de la instalación del usuario; no son referencias verificadas contra una revisión Git disponible aquí. El error declara fallo antes de enviar; el ledger y el DOM deben corroborar que no hubo envío previo o ambiguo antes de decidir reanudar.

| ID | Hallazgo / hipótesis | Grado de certeza | Prueba que la confirma o descarta |
|---|---|---|---|
| D01 | `ENSURE_CHAT_POLICY` no logró localizar la opción esperada | Confirmado por error | JSON/HTML/PNG y selector ejecutado. |
| D02 | La excepción de bootstrap llegó a `main` y terminó el proceso mostrado | Confirmado por traceback | Log completo, exit status y último state. |
| D03 | El menú no se abrió, se abrió otro menú o se leyó demasiado pronto | Hipótesis | Snapshot antes/después, roles, visibilidad y eventos del menú. |
| D04 | Etiqueta localizada, submenú, agrupación, portal o lista virtualizada | Hipótesis | Inventario real del menú y reproducción en fixture con comportamiento. |
| D05 | Modelo realmente ausente, deshabilitado o limitado para esa cuenta/superficie | Hipótesis | Menú completo observado y mensajes explícitos; ausencia de un selector no basta. |
| D06 | Modelo ya seleccionado pero ruta intenta buscarlo de nuevo | Hipótesis | Controles activos y estado checked/selected antes de abrir el menú. |
| D07 | Fuente, broker, prompts o instalación no corresponden al mismo bundle | Hipótesis | SHA-256 por componente y manifest de instalación. |
| D08 | Tras arreglar el selector pueden fallar writer, acciones, artefactos, CI o GO | Riesgo sistémico | Matriz completa y canaries live; no se afirma que ya estén rotos. |

Evidencia a recoger primero, sin borrar el run:

```text
/var/lib/ai-loop/logs/R20260922T024027.v3.log
/var/lib/ai-loop/state/R20260922T024027.v3.json
/var/lib/ai-loop/runs/R20260922T024027/browser/broker-diagnostics/
  2026-09-22T074042652Z-ENSURE_CHAT_POLICY.json
  2026-09-22T074042652Z-ENSURE_CHAT_POLICY.png
  2026-09-22T074042652Z-ENSURE_CHAT_POLICY.html
```

Leer JSON → PNG → HTML; registrar controles visibles, nombre accesible, rol, selected/checked, enabled, URL, superficie, identidad del proyecto, composer, turnos, browser epoch, idioma y versión. Capturar inventarios en el mismo instante del fallo y trazas de intentos. Conservar originales privados y usar copias saneadas para fixtures; no publicar tokens, cookies, claves o texto ajeno al incidente.

**Gate diagnóstico:** obtener una regresión roja sobre la base v4.2 y verde con la corrección usando evidencia del incidente. Si no se obtiene la evidencia original, registrar esa limitación y exigir reproducción live equivalente con nueva captura; no etiquetar una hipótesis como causa raíz confirmada.

## 3. RALPLAN-DR y ADR-043

### 3.1 Principios

1. Cada efecto requiere contexto verificado, intención persistida y reconciliación de resultado.
2. La política del usuario se aplica a hechos observados; un selector ausente no autoriza cambiar de modelo/superficie.
3. El broker es el único dueño del navegador; OpenCode interpreta, sin autoridad física.
4. Progreso acotado y recuperable: resolver errores transitorios y distinguir bugs, bloqueos y ambigüedad.
5. La aceptación exige evidencia del ciclo real y de su recuperación, ligada a revisiones concretas.

### 3.2 Tres criterios de decisión

1. Restablecer el arranque del incidente sin degradar la política documentada ni duplicar envíos.
2. Conseguir un ciclo completo con todas las integraciones realmente disponibles.
3. Mantener compatibilidad, trazabilidad y costo de implementación/pruebas razonables.

### 3.3 Alternativas evaluadas

| Opción | Ventajas | Costos / límites | Decisión |
|---|---|---|---|
| A. Parche mínimo del selector conservando política fija | Menor diff y recuperación rápida si la causa es una etiqueta/ubicación | No distingue catálogo incompleto de indisponibilidad; escasa defensa ante otros layouts | Viable como primer incremento verificable; insuficiente como entrega final. |
| B. Adaptador DOM basado en evidencia + política explícita versionada + verificación integral | Separa descubrimiento, elección y prueba; conserva defaults; permite aliases probados y diagnósticos concretos | Más contratos, migración y pruebas; riesgo de ampliar demasiado el resolver | **Elegida**, con conjunto pequeño de adaptadores y presupuesto acotado; no crear un navegador autónomo general. |
| C. Elegir manualmente el modelo y reutilizar el chat preparado | Útil para recuperar acceso y aislar el bug | Intervención repetitiva; no prueba bootstrap autónomo; no resuelve recuperación completa | Vía diagnóstica asistida, no aceptación final. |
| D. Aceptar cualquier modelo, desactivar la guarda o saltar a Work | Puede superar el punto de fallo | Viola política, costo/superficie y prueba de identidad | Rechazada por incompatibilidad con los principios. |

**Decisión ADR-043:** implementar B por incrementos: evidencia/regresión → resolver verificable → orquestación y contratos → integración/aceptación live. No reemplazar el controller ni el ownership del broker.

**Consecuencias:** se añade un esquema de política, pruebas de menús, taxonomía de errores, presupuestos y manifests; se preservan entrypoints y defaults. Un modelo no disponible sigue siendo un bloqueo real cuando no existe alternativa previamente autorizada. Ningún código interpreta “mejor modelo” mediante heurísticas o comparación de nombres.

**Seguimientos:** incorporar cada nuevo layout observado como fixture revisada; actualizar aliases solo con evidencia; medir tasas de resolución y bloqueos sin convertir fallos en PASS.

## 4. Equipo de implementación: seis integrantes

Tamaño total: **6 agentes/personas, incluido el coordinador**. Cinco carriles de trabajo más integración. No se necesitan nombres de agentes ajenos a la instalación ni modelos específicos.

| ID | Rol | Responsabilidad / propiedad primaria | Razonamiento sugerido |
|---|---|---|---|
| TL | Coordinador, arquitectura e integración | Contratos, repos/rama, dependencias, resolución de conflictos, gates y entrega | Alto; máximo disponible para decisiones irreversibles o invariantes. |
| BR | Ingeniería de browser | `browser-broker-v1.cjs`, adaptadores, inventario y pruebas DOM | Alto. |
| FSM | Controller, estado y transporte | `ai-loopd-v3.py`, migraciones, ledgers, acciones y recuperación | Alto; máximo para ventanas de crash. |
| INT | Integraciones y protocolo | GitHub, CI/Semaphore, VPS, OpenCode, manifests de capacidad y prompts | Alto. |
| QA | Validación independiente | Contratos de aceptación, fixtures adversariales, E2E, fault injection, evidencia y veredicto | Alto; máximo para revisión final. |
| REL | Release y operación | Preflight, instalación, backups, rollback, scripts de verificación y runbook | Medio/alto; alto para instalación/migración. |

QA puede escribir pruebas pero no autoaprobar cambios funcionales de su autoría: TL revisa los tests y QA revisa el comportamiento producido por otros. Cada tarea tiene un dueño y otro revisor. BR/FSM/INT colaboran por contratos; ningún par escribe simultáneamente el mismo archivo compartido. TL serializa integración y congela la revisión que se entrega a QA. REL no reinicia Chrome mientras BR lo inspecciona.

Roster de ejecución en OpenCode según la skill: `general` para los cinco especialistas y revisiones; `explore` para descubrimiento acotado. Verificar disponibilidad local antes de lanzar. Roles Planner/Architect/Critic son responsabilidades, no nombres mágicos de subagentes. En esta planificación se usa el mecanismo de colaboración disponible para revisores secuenciales porque `task()` nativo de OpenCode no está expuesto; no se afirma haberlo ejecutado.

## 5. Diseño obligatorio del bootstrap y política de modelo

### 5.1 Configuración con compatibilidad explícita

La base documentada exige **Chat + GPT-5.6 Sol + High**. Conservar esa combinación como default de migración; este plan no autoriza sustituirla por cualquier otro modelo. Los nombres aquí son datos del runtime existente, no asignaciones de modelo al equipo.

Crear un esquema versionado de `chat_policy` con: `surface`, `selection_mode` (`strict` o `ordered_allowlist`), pares de identidad/reasoning admitidos, aliases UI comprobados por locale, preferencia explícita, y presupuesto de resolución. Las alternativas comienzan vacías. `ordered_allowlist` solo se activa con una configuración autorizada que enumere los pares exactos; no inferir equivalencias como High=Max ni Sol=Light. Registrar origen y hash de la política efectiva.

El parser documentado solo lee `repo`, `branch` y `project_url`. Por ello **añadir claves YAML sin ampliar y probar el parser no implementa la política**. Elegir una única fuente autoritativa, validar claves y tipos, rechazar contradicciones YAML/env/CLI y definir precedencia documentada. Migrar config ausente al default estricto; no rellenar alternativas. Mantener la configuración/modelo existente de OpenCode separado de la política de Chat.

Una política se fija al iniciar el run y se registra con hash; no cambiarla a mitad de una operación o iteración silenciosamente. Si requiere cambio autorizado, crear un checkpoint y transición auditada tras resolver operaciones ambiguas.

### 5.2 Pipeline de resolución del broker

1. Validar ownership/lock, epoch, página objetivo, autenticación y proyecto. `TARGET` requiere señales actuales del contexto activo; un link del proyecto en el sidebar por sí solo no basta.
2. Distinguir bootstrap nuevo de resume: nuevo exige draft vacío del proyecto; resume mantiene el chat ligado al run y reconcilia ledger.
3. Observar **controles activos** de superficie/modelo/reasoning. Si ya satisfacen la política, generar prueba sin clicks innecesarios.
4. Si hace falta cambio, abrir el control correcto y demostrar que su menú está visible. Usar rol/nombre accesible y alcance del menú activo; no buscar `Sol` en todo el body ni usar `.first()` para ocultar ambigüedad.
5. Inventariar candidatos visibles, disabled, checked/selected, agrupaciones y submenús. Explorar solo controles conocidos, con presupuesto de profundidad/acciones. Manejar listas virtualizadas con desplazamiento acotado y evidencia de progreso. No asumir inventario completo si no puede probarse.
6. Normalizar espacios/case/localización con aliases versionados; mantener identidad de variantes y reasoning. No usar substring o fuzzy matching para decidir el modelo.
7. Resolver un candidato permitido y único. Diferenciar `MENU_NOT_OPEN`, `CATALOG_INCOMPLETE`, `MODEL_UNAVAILABLE`, `AMBIGUOUS_MODEL_MATCH`, `MODEL_DISABLED` y `UI_CONTRACT_CHANGED`.
8. Seleccionar y volver a leer estado activo. La UI puede cambiar/reiniciar reasoning al cambiar modelo: resolverlo y verificarlo después. Si está dividido en dos controles, probar ambos y su asociación.
9. Cerrar el menú si interfiere con composer; volver a observar proyecto, superficie, modelo, reasoning y draft/conversación. Esperar predicados concretos con deadline; no sleeps ciegos ni `force:true` para saltar actionability.
10. Devolver `PASS` solo con prueba completa. Una captura es evidencia diagnóstica; la selección la demuestran controles/estados del DOM activo y consistentes.

Localizadores y auto-waiting se apoyan en las guías oficiales [S1–S2]; el contrato exacto del selector de ChatGPT debe salir del DOM del usuario. No consultar endpoints internos no documentados ni eludir login, 2FA o CAPTCHA.

### 5.3 Prueba de política y guarda antes de cada envío

Contrato nuevo propuesto, a implementar y versionar:

```json
{
  "schema_version": 1,
  "status": "PASS",
  "run_id": "<run>",
  "iteration": 0,
  "broker_epoch": "<epoch>",
  "page_binding": "<id de página/draft/chat observado>",
  "project_id": "<id configurado y demostrado>",
  "surface": "chat",
  "model_key": "<identidad canónica permitida>",
  "reasoning_key": "<identidad permitida para ese modelo>",
  "policy_sha256": "<hash>",
  "observed_at": "<UTC>",
  "selected_evidence": ["<control activo, estado y valor>"],
  "diagnostics": {"json": "<ruta>", "screenshot": "<ruta>"}
}
```

El controller valida esquema, binding, hash y epoch. `SEND_ATOMIC` reobserva inmediatamente antes de enviar; no reutiliza un PASS antiguo si cambió navegación, pestaña, sesión, modelo, reasoning, epoch o política. La guarda de **draft vacío** se aplica solo al primer envío de un chat nuevo, no a evidencias/follow-ups de una conversación existente.

Si la selección se pierde después de adjuntar, se corrige únicamente si preserva el composer y su contexto; después se revalida el adjunto. Si debe navegar/recrear draft, invalidar todas las pruebas asociadas y reanudar desde un checkpoint seguro sin duplicar el envío.

### 5.4 Tratamiento de errores y progreso

| Categoría | Ejemplos | Conducta |
|---|---|---|
| Transitorio resoluble | DOM aún cargando, broker reiniciable, EOF en GitHub | Retry acotado por deadline/backoff y reobservación; sin side effects duplicados. |
| Defecto interno | Parser, selector/adaptador roto, esquema inválido | `BLOCKED_INTERNAL`, evidencia y corrección; no etiquetarlo como bloqueo humano. |
| Dependencia externa | Login/2FA, permiso revocado, modelo demostrado no disponible | `BLOCKED_EXTERNAL` con acción exacta para resolver; conservar el run. |
| Resultado ambiguo | Send o comando pudo ejecutarse | `RECONCILIATION_REQUIRED`; no repetir a ciegas ni inferir éxito. |

Una capa de salida en `main` debe persistir error tipado, etapa, diagnóstico y estado recuperable, cerrar recursos propios y devolver código no cero. Conservar traceback completo para depuración; evitar que sea la única salida o que se pierda el checkpoint. No convertir excepciones en PASS.

Añadir presupuestos configurables para bootstrap, descubrimiento, retries, espera CI, respuesta, progreso sin cambios y total del run. Reusar variables existentes de v4.2 donde correspondan; nuevas variables llevan esquema, defaults documentados, límites y pruebas. Reloj monotónico para duración; UTC para auditoría. Agotar presupuesto genera estado explicado y reanudable, no bucle infinito.

## 6. Contratos del ciclo completo

### 6.1 Estado y transición

Preservar las fases existentes (`IMPLEMENTING`, `WAIT_CI`, `FAILURE_ANALYSIS`, `FINAL_REVIEW`, `DONE`), añadiendo subestado de bootstrap y estados de bloqueo compatibles. Guardar `state_schema_version`, `run_id`, iteración, repo/rama, baseline/candidate, chat binding, hashes de plan/política/release y referencias de artefactos. El hash de release cambia solo mediante migración/checkpoint auditado.

Persistencia atómica y duradera antes/después de efectos, con lock global y por run. Validar garantías reales del filesystem de `/var/lib/ai-loop`; tratar state corrupto/versión desconocida sin truncarlo. No llamar a `start-loop-v3` para continuar un run existente.

### 6.2 Envíos, respuestas y semántica

- Ledger `READY → SENDING → SENT / AMBIGUOUS` ligado a run, iteración, chat, propósito, payload/adjunto y `delivery_id`. Una coincidencia de texto en un turno anterior u otro chat no confirma entrega.
- Tras caída luego del click, buscar marcador en el chat correcto y reconciliar; no usar nuevo ID para reenviar el mismo efecto.
- Leer respuestas finalizadas del assistant posteriores al delivery esperado; excluir mensajes antiguos, user messages, eco de logs, ejemplos de `GO` y bloques citados.
- `GENERATING` y `RATE_LIMIT` esperan/backoff; no interrumpir generación ni cambiar superficie/modelo. Tras reinicio persisten timestamps y fingerprints.
- OpenCode devuelve eventos con esquema y binding al mensaje/hash. Si la salida es inválida se reintenta interpretación, no acciones. Conflictos semánticos requieren evidencia o pregunta específica al mismo chat.
- `SELF_CONTINUE` genera `procede` una vez por fingerprint; no_commit, diagnóstico y replan tienen idempotencia y presupuesto propio. Las etapas de failure analysis tienen prioridad sobre follow-ups genéricos.

### 6.3 Acciones y ventana de crash

Materializar comandos desde bloques de la respuesta mediante `block_index`, `message_id`, SHA-256 y longitud UTF-8; verificar nuevamente en controller. Nunca reconstruir bytes desde una respuesta del LLM. Target siempre explícito: `local`, `vps`, `github-readonly`; no redirección implícita local→VPS.

El ledger de acciones incorpora intención persistida, `execution_id`, target, cwd/host, hash, clase de efecto (`read_only`, `idempotent_with_key`, `non_idempotent`), inicio, resultado/receipt y entrega de evidencia. Si el proceso cae después de ejecutar y antes de guardar resultado, **un simple set `processed_actions` no garantiza ejecución única**. Reconciliar mediante receipt durable del ejecutor/wrapper; para efectos no reconciliables, bloquear como resultado desconocido. Solo repetir automáticamente acciones demostrablemente read-only o con clave idempotente y contrato de reejecución.

Matar/timeout: capturar proceso/grupo y resultado real. Cortar SSH no prueba que murió el comando remoto; registrar estado remoto desconocido hasta obtener receipt. Una acción con exit no cero también devuelve stdout/stderr y contexto al chat. Ningún timeout se trata como éxito.

Preservar prohibiciones: operator sin commit/push/reset/clean, raw SSH/scp/sftp, mutación arbitraria ni cambios en `/tmp/log`. La reproducción CI corre aislada, sin credenciales de producción y con runner/policy restringidos: que el comando empiece por `pytest` no garantiza que el código del test sea inocuo. No trasladar permisos del escritor Git al operator.

### 6.4 Artefactos y evidencia

`ATTACH_FILE`: relacionar archivo, hash/tamaño local, estado de upload completo y chip/composer activo; filename encontrado en body o input cargado sin upload terminado no basta. Cuando la UI no expone hash remoto, registrar esa limitación y correlacionar fuente verificada + upload + turno enviado, sin inventar comprobación de bytes del servidor.

`DOWNLOAD_ARTIFACT`: obtener bytes reales del enlace de la última respuesta finalizada; soportar rutas documentadas v4.2 con wrappers que mantengan política de destinos/tamaño. Verificar UTF-8, tamaño, hash, estructura, basename seguro y vínculo con run/iteración/mensaje. Rechazar login HTML disfrazado, archivo vacío, homónimo viejo, path traversal o descarga parcial. Validar estructura del plan (objetivo, equipo, tareas, tests, gates), no solo extensión. Escribir primero temporal y finalizar atómicamente.

Si falta artefacto: estado `PLAN_ARTIFACT_*`, follow-up correctivo acotado y esperar respuesta nueva; no fabricar un plan de un fragmento inline ni avanzar iteración sin archivo válido. Evidencia grande se adjunta una sola vez, con manifest de hashes y truncación explícita si hay límites.

### 6.5 Candidato, CI, despliegue y GO

Un HEAD distinto al baseline es señal de candidato, no prueba de autoría ni de pertenencia a la iteración. Validar repo/rama, ascendencia, parent y evidencia de implementación; si aparece un commit ajeno concurrente, bloquear/reconciliar. Conservar un commit consolidado por iteración de implementación y escritor único. Un ciclo de remediación puede producir otra iteración/otro commit; no exigir un único commit para toda la historia de recuperación.

Manifest CI: `repo`, `branch`, `candidate_sha`, provider, proyecto CI, run, pipeline, intento/rerun, jobs requeridos, estado terminal, conclusión, URL y timestamps. Consultar por SHA exacto; paginar fuentes y tratar respuestas incompletas/UNKNOWN como pendientes o error explicado. Los checks/statuses sin jobs esperados nunca implican éxito por conjunto vacío. No usar el último pipeline de la rama como sustituto de identidad. Consultar Checks y/o commit statuses según la integración realmente configurada [S3].

Un nuevo rerun invalida evidencia terminal anterior de ese pipeline/intento. `skipped`, `neutral`, `cancelled` o checks opcionales verdes no satisfacen la política de jobs obligatorios. Definir provider/checks requeridos en configuración; si hay fallback entre proveedores, debe estar autorizado y mapeado, nunca inferido a partir de cualquier check verde. Para este caso Semaphore debe probarse realmente, incluso si existen otros CI.

Antes de aceptar `FINAL_GO`, reconsultar HEAD, el conjunto completo de CI requerido y el intento vigente; verificar entrega de evidencia, cero pendientes/ambigüedades, modelo/contexto correctos y relación de la respuesta final con la solicitud de revisión de ese candidato. Si hubo commit nuevo durante `FINAL_REVIEW`, invalidar el GO antiguo y volver a validar el nuevo candidato. Escribir prueba por run y actualizar el alias global `go_confirmed.json` sin permitir que evidencia vieja cierre otro run.

El cierre registra el intervalo de observación y lee HEAD antes y después de consultar CI; ambas lecturas deben coincidir con el candidato. El GO certifica esa revisión y esas observaciones fechadas, no congela la rama ni garantiza que un tercero no la cambie después. Conservar identidad/intento y timestamps para auditar esas carreras.

Si hay despliegue requerido, obtener receipt con SHA/artefacto desplegado, target y validación de salud/servicio definida por el proyecto. Separar `CI_SUCCESS` de `DEPLOYMENT_VERIFIED`; no operar trading/órdenes reales para probar el loop.

## 7. Preflight de capacidades y herramientas obligatorias

Comprobar binarios instalados es necesario pero insuficiente. Producir `capabilities.json` con versión, identidad, operación probada, resultado, evidencia, timestamp y si el requisito es obligatorio. Un requisito obligatorio `UNKNOWN`, `SKIPPED` o `UNAVAILABLE` impide aceptación.

Cada capacidad separa `DISCOVERED` (identificada), `FEASIBLE` (interfaces/permisos compatibles observados) y `LIVE_PROVEN` (operación real completada). G0 exige factibilidad documentada del escritor; T39/G3 exige commit/push real y eleva su estado a `LIVE_PROVEN`. Así el preflight no depende circularmente de un canary que todavía está habilitando.

| Componente | Prueba mínima real | Evidencia requerida |
|---|---|---|
| Python/controller + Node/broker | Arranque compatible, RPC válido, ownership único | Versiones, hashes, epoch, request/response correlacionados. |
| Playwright/Chrome/perfil | Sesión dedicada, proyecto y política demostrados sin enviar | Prueba DOM, snapshot/PNG, no incremento de user turns. |
| Chat escritor | Herramienta/conector de escritura autorizado visible y operativo en superficie Chat | Primero inspección de capacidades; luego commit/push real en canary y SHA retornado corroborado externamente. |
| Git/gh read-only | Identidad/permisos mínimos y acceso al repo/rama exactos | Respuesta saneada, branch HEAD, tree/parent; ninguna mutación del operator. |
| OpenCode | Clasificar respuesta de prueba con esquema y hash vinculados | Evento válido y rechazo de salida malformada; conservar modelo/proveedor configurado. |
| Ejecutor local | Comando read-only con nonce, stdout/stderr y exit code conocidos | Receipt vinculado al bloque real del chat. |
| Wrapper VPS | Host permitido y probe read-only que refleje nonce | Identidad del host, output, rc, duración y receipt; ningún raw SSH en operator. |
| `ci-status` | Consulta exacta de candidato conocido y rama correcta | JSON de provider/run/pipeline/attempt/SHA; casos pending/failure/success. |
| Semaphore | Leer estado y logs de pipeline/job exactos | Sesión/API autorizada, identidad completa y logs saneados verificables. |
| Transporte de artefactos | Adjuntar plan/evidencia y descargar un `.md` generado en el chat | Hash local, delivery proof, origen/mensaje y descarga válida. |
| Prompts/skills | Chat entiende protocolo de acciones, diagnóstico y replan | Respuestas y artefactos conformes; un slash command escrito no demuestra que una skill esté instalada. |

**Riesgo de capacidad decisivo:** la documentación atribuye commit/push al Chat y los prohíbe al operator. No asumir que “tener GitHub conectado” implica escritura. Si esa superficie/cuenta no dispone de escritor autorizado, registrar `CHAT_WRITER_UNAVAILABLE`; no pedir infinitamente commit, no habilitar git push al operator y no saltar a Work. El equipo debe resolver la capacidad con una integración compatible y autorización existente; si requiere cambio de arquitectura/permisos del usuario, entregar bloqueo concreto. Mientras persista, el objetivo permanece incumplido.

La capacidad de crear artefactos descargables también debe probarse. Si el entorno no resuelve `/skillsbench` o `/ralplan`, entregar las instrucciones completas de la skill/protocolo en el contexto permitido y validar el resultado; no tratar la invocación textual como ejecución confirmada.

## 8. Backlog atómico asignado y dependencias

Cada fila produce una unidad revisable. `R` indica revisor distinto al dueño. Los tests `Txx` se definen en §9. Una tarea se cierra con evidencia, no con “implementado”. Duración y paralelismo se ajustan después del inventario, sin omitir gates.

**Cambios mínimos guiados por evidencia:** si el código existente ya satisface el contrato de una tarea, cerrarla como `VERIFIED_EXISTING` con revisión, ruta/símbolo y prueba aplicable, sin reimplementar preventivamente. Esto no permite omitir pruebas de integración/live ni declarar cumplimiento únicamente por la documentación. Priorizar regresión del incidente y canary temprano cuando estén resueltas sus dependencias.

### Hito M0 — Hechos y contratos antes de reparar

| ID | Dueño / R | Dependencias | Tarea y criterio de aceptación |
|---|---|---|---|
| B01 | TL / REL | — | Identificar raíz/rama/HEAD/dirty state/AGENTS del control plane y del target; registrar manifest y proteger cambios ajenos. |
| B02 | REL / QA | B01 | Copiar evidencia exacta del incidente y state/ledger; manifest con hashes, timestamps y copia saneada. Ausencias declaradas. |
| B03 | BR / QA | B02 | Localizar la ruta real de `ENSURE_CHAT_POLICY` y capturar inventario de controles del fallo; vincular cada selector a evidencia. |
| B04 | QA / BR | B03 | Construir regresión del incidente ejecutando broker real contra fixture comportamental; debe fallar en base v4.2 (T01). |
| B05 | TL / FSM | B01–B03 | Congelar contratos de policy, proof, capacidades, action receipt y CI manifest con ejemplos positivos/negativos. |
| B06 | INT / TL | B01 | Inventariar autenticación/capacidades de writer, GitHub, VPS, Semaphore, OpenCode y artefactos; declarar requisitos para canary (T20). |

### Hito M1 — Resolver política sin saltar guardas

| ID | Dueño / R | Dependencias | Tarea y criterio de aceptación |
|---|---|---|---|
| B07 | FSM / TL | B05 | Implementar parser/schema de política y precedencia; migración al default estricto y rechazo de claves ignoradas (T02). |
| B08 | BR / QA | B03,B05 | Implementar observación de selección activa y fast path sin clicks; solo controles del contexto activo (T03). |
| B09 | BR / QA | B08 | Implementar apertura comprobada del menú e inventario acotado con submenús/virtualización documentados (T04–T05). |
| B10 | BR / TL | B07,B09 | Resolver aliases y candidatos permitidos únicos; separar catálogo incompleto de modelo ausente (T06–T07). |
| B11 | BR / QA | B10 | Seleccionar modelo/reasoning y probar estado después de cerrar menú; detectar reset/ambigüedad (T08). |
| B12 | BR / FSM | B04,B11 | Emitir proof versionada y errores tipados con diagnóstico de cada intento; regression T01 verde. |
| B13 | FSM / BR | B07,B12 | Consumir proof y revalidar contexto/política en cada Send, con invalidación de epoch/navegación (T09). |
| B14 | REL / BR | B12 | Añadir doctor no-send y resumen efectivo de policy/catalogue, con stdout JSON legible y evidencias (T10). |

### Hito M2 — Durabilidad, acciones y progreso

| ID | Dueño / R | Dependencias | Tarea y criterio de aceptación |
|---|---|---|---|
| B15 | FSM / QA | B05 | Implementar state schema/migración atómica conservando todas las identidades y ledgers (T11). |
| B16 | FSM / REL | B15 | Manejar bootstrap/excepciones en frontera del daemon con exit no cero, checkpoint y cleanup propio (T12). |
| B17 | FSM / QA | B13,B15 | Reconciliar Send en todas las ventanas de crash y deduplicar por operación/chat (T13). |
| B18 | FSM / INT | B05,B15 | Persistir intención/receipt de acciones y resultado desconocido; definir reejecución por clase (T14). |
| B19 | INT / FSM | B18 | Extender wrapper/ejecutor con receipts durables, timeout y consulta de estado, sin abrir permisos de operator (T15). |
| B20 | FSM / QA | B17,B19 | Entregar stdout/stderr/evidencia grande una vez por receipt, conservando hashes y errores (T16). |
| B21 | FSM / INT | B15 | Vincular respuestas/eventos semánticos al delivery y limitar `procede`/no_commit/diagnosis/replan (T17–T18). |
| B22 | FSM / REL | B16,B21 | Configurar deadlines/backoff/watchdog de progreso con clasificación interna/externa/ambigua y resume (T19). |

### Hito M3 — Integraciones, planes y GO

| ID | Dueño / R | Dependencias | Tarea y criterio de aceptación |
|---|---|---|---|
| B23 | INT / TL | B05,B06 | Implementar capabilities manifest y gate de writer/artefactos en Chat; verificar errores accionables (T20). |
| B24 | INT / FSM | B05 | Implementar contrato OpenCode/eventos con versiones, esquema y binding al mensaje/hash (T21). |
| B25 | BR / INT | B12 | Fortalecer adjunto completo ligado al composer/turno y evidencia verificable (T22). |
| B26 | BR / QA | B12 | Validar descargador real `.md` con provenance, contenido, hash, rutas y atomicidad (T23). |
| B27 | INT / FSM | B01,B05 | Correlacionar candidato con repo/rama/iteración/parent y detectar cambios concurrentes (T24). |
| B28 | INT / QA | B06,B27 | Normalizar CI exacto con checks esperados, paginación, intentos/reruns y estados incompletos (T25). |
| B29 | INT / QA | B28 | Extraer logs Semaphore del job/run/pipeline/SHA exactos, con autenticación y redacción verificadas (T26). |
| B30 | INT / TL | B29 | Reproducir fallo en checkout aislado del candidato, sin secretos ni permisos de producción (T27). |
| B31 | FSM / INT | B21,B24,B26,B29 | Completar FSM evidencia→diagnóstico→replan→descarga→nuevo chat; nueva baseline y candidato vacío (T28). |
| B32 | FSM / QA | B20,B23,B27,B28,B31 | Endurecer gate GO y prueba por run; invalidar GO ante cambio HEAD/rerun/pendientes (T29). |
| B33 | INT / TL | B23,B31 | Parametrizar prompts por repo/rama/propósito; anexar protocolo/skill disponible y un commit por iteración (T30). |
| B34 | INT / QA | B19,B28 | Implementar verificación operacional del target cuando el manifest exige despliegue (T31). |

### Hito M4 — Verificación, instalación y aceptación

| ID | Dueño / R | Dependencias | Tarea y criterio de aceptación |
|---|---|---|---|
| B35 | QA / TL | B04,B05 | Formalizar matriz T01–T43 y runner que falla ante requisito omitido/skip; correlación Bxx→Txx→evidencia. |
| B36 | QA / BR | B12,B13,B25,B26 | Ejecutar suite DOM real contra fixtures adversariales y regresiones legacy; capturar trace de fallos. |
| B37 | QA / FSM | B17–B22,B31,B32 | Implementar matriz de crash/fault injection y soak reproducible, con seed y oráculos de duplicados (T32–T34). |
| B38 | QA / INT | B23–B34 | Ejecutar integración multiproceso con adapters reales y servicios simulados; probar contratos negativos (T35). |
| B39 | REL / FSM | B07,B15,B33 | Preparar instalación atómica del bundle, manifest de hashes/config y migración/rollback compatibles (T36). |
| B40 | REL / QA | B14,B23,B28,B39 | Implementar preflight integral y comandos de aceptación con modos no-send/live claramente separados (T37). |
| B41 | TL / QA | B35–B40 | Integrar/fijar revisión y cerrar defectos P0/P1; ejecutar gates offline sobre la revisión exacta. |
| B42 | REL / QA | B41 | Instalar bundle validado; comparar hashes fuente/runtime y probar stop/restart/rollback aislado (T36–T37). |
| B43 | BR / QA | B42 | Ejecutar bootstrap live no-send en perfil real y demostrar policy/adjunto; cero mensajes (T38). |
| B44 | INT / QA | B43 | Ejecutar canary happy path real con Chat, writer, OpenCode, local, VPS, GitHub y Semaphore hasta GO (T39). |
| B45 | INT / QA | B44 | Ejecutar fallo CI controlado en entorno aislado y recuperación completa con replan real hasta GO (T40). |
| B46 | FSM / QA | B44 | Ejecutar restart live tras Send y tras acción read-only; demostrar reconciliación sin duplicados (T41). |
| B47 | TL / QA | B45,B46 | Ejecutar objetivo real en `Trochez/bot_trading:feature/GRU`, con alcance seguro y manifest aprobado, hasta GO (T42). |
| B48 | QA / TL | B47 | Auditar evidencia y hashes de todos los gates; producir veredicto reproducible `FULL_LOOP_ACCEPTED` o NO_GO (T43). |
| B49 | REL / QA | B48 | Entregar bundle, runbook, matriz, limitaciones y reporte fechado; documentar recuperación del run original. |

**Paralelismo recomendado:** tras B05, BR trabaja M1; FSM en B07/B15/B18; INT en capacidades/CI; QA en contratos/fixtures; REL en manifest/installer. TL asigna ventanas únicas para archivos compartidos. M4 live es serial por ownership del browser/target. Ruta crítica: B02–B04 → B08–B13 → integración de M2/M3 → B41–B48. Un bloqueo de writer se resuelve temprano, no después de semanas de refactor.

## 9. Plan de pruebas y oráculos de aceptación

Regla: probar código de producción, no una copia simplificada que vuelve PASS por construcción. Los dobles representan dependencias externas y deben detectar acciones/eventos; no sustituir la función bajo prueba. Preservar suites v4.1/v4.2 y comprobar rutas legacy relevantes. No exigir cobertura porcentual arbitraria como sustituto de invariantes; sí ejecutar todos los escenarios obligatorios siguientes.

### 9.1 Unitarias y browser con fixtures comportamentales

| Test | Escenario | Resultado verificable |
|---|---|---|
| T01 | Evidencia/layout del incidente | Base reproduce fallo; patch selecciona correctamente si opción existe; si no, clasifica indisponibilidad con evidencia, sin Send. |
| T02 | Config ausente/válida/inválida, precedence, clave ignorada, alias contradictorio | Default legacy idéntico; errores explícitos; hash efectivo estable; alternativas no inventadas. |
| T03 | Modelo ya correcto; texto “Sol/High” solo en historial; proyecto solo en sidebar | Fast path sin clicks solo ante selección/contexto activo probado; nunca falsos PASS. |
| T04 | Menú cerrado, menú equivocado, portal, rerender/stale node, overlay | Localizar/abrir menú correcto o error tipado; ningún click ambiguo. |
| T05 | Locale ES/EN, grupos/submenú, opciones virtualizadas, loading lento | Descubrir con límites y progreso; `CATALOG_INCOMPLETE` si exploración no prueba totalidad. |
| T06 | Ausente/disabled/duplicado/Light parecida/unknown; candidato permitido diferente | Elegir únicamente identidad y reasoning autorizados; strict nunca hace fallback. |
| T07 | Falta opción antes de cargar, menú exhaustivo sin opción, rate limit | Diferenciar transitorio, indisponible y límite; no declarar ausencia por timeout genérico. |
| T08 | Click sin selección, selected ambiguo, modelo resetea reasoning | Leer estado final; rechazar prueba insuficiente; recuperar reasoning solo si permitido. |
| T09 | Cambio de modelo/proyecto/página/epoch después de PASS y antes de Send | Invalidar proof y impedir envío; follow-up válido no exige 0 turnos. |
| T10 | Doctor no-send sobre chat existente y draft | JSON útil; cero nuevos turnos, cero uploads/envíos no solicitados; ownership respetado. |
| T11 | States v4.1/v4.2, state truncado, versión futura, procesos concurrentes | Migración preserva ledgers; corrupción/versión desconocida no se sobreescribe; un solo owner. |
| T12 | Excepción en cada fase de bootstrap/cleanup | Error duradero, rc no cero, recursos propios cerrados; sin éxito aparente ni proceso huérfano. |
| T13 | Crash antes/después click, marcador tardío, marcador en otro chat | A lo sumo un efecto de envío; reconciliación por binding; ambiguo no se reenvía. |
| T14 | Crash tras comando antes de persistencia; action ID repetido con bytes distintos | Receipt resuelve o estado desconocido; hash distinto rechaza; no repetición insegura. |
| T15 | VPS timeout/desconexión/proceso remoto aún activo/receipt tardío | No asumir cancelación; wrapper identifica ejecución y permite consulta sin repetirla. |
| T16 | stdout/stderr grandes, exit 1/124/125/126, evidencia ya enviada | Entrega completa o truncación declarada con archivo; un único delivery por resultado. |
| T17 | GENERATING, SETTLED antiguo, respuesta editada, fingerprint repetido | Procesar solo respuesta autoritativa vinculada; `procede` una vez; nada durante generación. |
| T18 | No commit, plan inline, diagnosis pendiente, salidas ambiguas | Follow-ups específicos y acotados; failure stage no se salta por bucle genérico. |
| T19 | Budgets agotados, reloj de pared cambia, broker muere, EOF/red intermitente | Reintentos con deadline y resume estable; estados internos/externos correctos. |

### 9.2 Contratos e integración

| Test | Escenario | Resultado verificable |
|---|---|---|
| T20 | Binario existe pero auth/permiso/capacidad writer falta | Preflight identifica requisito faltante; no false-green, no bypass del operator. |
| T21 | OpenCode JSON inválido, evento desconocido, SHA/mensaje falso | Rechazo sin ejecución; retry semántico permitido y acotado. |
| T22 | Archivo en input sin upload, nombre en historial, adjunto equivocado | No Send; solo composer/turno y upload completo sirven como prueba. |
| T23 | Download HTTP/blob/data/evento, HTML/login, parcial, vacío, viejo, UTF-8 inválido, ruta maliciosa | Artefacto real válido o error; hash/provenance correctos, no escape del directorio. |
| T24 | HEAD nuevo ajeno, branch con `/`, parent incorrecto, concurrencia | Candidato atribuible al repo/iteración; reconciliar ajenos; tratar ref correctamente. |
| T25 | CI missing/empty/UNKNOWN/pending, otro SHA, jobs parciales, rerun/skip/cancel | Solo conjunto requerido completo y vigente es SUCCESS; paginación y timeouts cubiertos. |
| T26 | Semaphore job parecido o intento anterior, login vencido, logs largos | Correlación exacta o bloqueo; no usar logs del vecino; secretos saneados. |
| T27 | Reproducción CI del SHA fallido, comando de test que intenta red/mutación externa | Checkout exacto; aislamiento/policy niegan efectos; resultado no suplanta CI real. |
| T28 | CI failure→logs→diagnosis→plan faltante→plan real→nuevo chat | Una transición por mensaje/artefacto; baseline/iteración correctas y sin mezclar chats. |
| T29 | GO prematuro/citado/de otro chat/de otro SHA; HEAD o rerun cambia | Rechazo; GO solo tras pruebas actuales y cero pendientes; alias global no contamina. |
| T30 | Prompt del control plane y prompt target | Repo/rama correctos, capacidad operator explícita, un commit por iteración, no destino heredado erróneo. |
| T31 | CI verde pero despliegue ausente/SHA distinto/salud fallida | No GO cuando deploy es requerido; receipt exacto y salud verificada para aceptar. |
| T32 | Crash matrix en side effects y checkpoints | Probar cada frontera de intención/ejecución/receipt/entrega y conservar invariant de no duplicación. |
| T33 | Payload UTF-8 exacto, hashes alterados, shell quoting, target ausente, instrucciones en logs | No ejecutar bytes alterados/targets implícitos ni comandos derivados de logs sin protocolo. |
| T34 | 100 secuencias deterministas con seeds guardadas: fallos/recuperación/rate limits | Cero duplicados, cero GO falsos, progreso o bloqueo tipado dentro del presupuesto. |
| T35 | Python + broker Node + OpenCode adapter + executor + CI/download dobles | RPC/esquemas/timeouts reales; flujo completo y fallos simulados sin monkeypatch de guardas; campos de eventos del §12 y vínculos a evidencia validados. |
| T36 | Instalación fallida a mitad, versiones mezcladas, rollback con state nuevo | Runtime coherente o versión anterior íntegra; no pérdida de estado ni downgrade incompatible. |
| T37 | Preflight invocado con run activo/perfil ocupado/dependencia ausente | Respeta lock; diagnóstico específico; comandos de gates fallan en skip/UNKNOWN. |

### 9.3 E2E live obligatorios

| Test | Recorrido | Criterio de éxito |
|---|---|---|
| T38 | Bootstrap real sin enviar | Proyecto, draft y política probados desde sesión real; cero user turns nuevos. |
| T39 | Happy path real, al menos tres intercambios de evidencia | Chat→local, Chat→VPS y Chat→GitHub/CI; escritor real produce candidato; Semaphore real verde; GO independiente. |
| T40 | Fallo CI controlado y reparación real en destino aislado | Pipeline falla de verdad; logs exactos vuelven; diagnosis y plan `.md` real; nuevo chat/candidato; CI verde y GO. |
| T41 | Dos reinicios live: después de Send y tras probe read-only ejecutado | Mismo run/chat/ledger; cero duplicados y continuación hasta GO, sin `continúa` manual. |
| T42 | Plan funcional real en `Trochez/bot_trading:feature/GRU` | Alcance previamente delimitado, candidato nuevo atribuible, CI requerido verde, VPS según manifest, GO actual. |
| T43 | Verificador sobre manifest/evidencia final y casos adulterados | Acepta conjunto completo y coherente, incluidos campos de eventos del §12 y vínculos evento→evidencia; rechaza hash cambiado, test omitido, skip obligatorio y GO viejo. |

T34 es una campaña definida, no un retry infinito hasta que algo pase. Usar las mismas seeds antes/después; guardar fallos iniciales y cambios. Si hay flakiness, investigar y corregir; no esconderla aumentando reintentos ni contar una corrida verde casual como resolución.

## 10. Canaries y gates de liberación

Todos los gates son obligatorios. Las pruebas destructivas o de fallo intencional se hacen con infraestructura aislada, sin credenciales/órdenes de trading ni despliegue a producción. El manifest define qué rutas CI son seguras antes del primer push.

| Gate | Dueño | Evidencia / condición de salida |
|---|---|---|
| G0 — Hechos y factibilidad | TL + INT | Evidencia/hipótesis clasificadas, contratos y capacidades. Writer en Chat factible; desconocidos críticos visibles. |
| G1 — Offline | QA | T01–T37 y suites heredadas relevantes verdes; regresión original cubierta; ningún test obligatorio omitido. |
| G2 — Instalado y no-send | REL + BR | Hashes del runtime = bundle validado, migración/rollback y T38 verdes. |
| G3 — Happy path live | INT + QA | T39, candidato/CI/GO reales y matriz de herramientas completa. |
| G4 — Recovery live | INT + QA | T40 y T41 verdes; ningún reset/edición manual del state para avanzar. |
| G5 — Target y cierre | TL + QA | T42/T43, reporte independiente y `FULL_LOOP_ACCEPTED`. |

### 10.1 Plan canary de éxito

REL/INT crearán un archivo `AI_LOOP_FULL_ACCEPTANCE_<timestamp>.md` con repo/rama explícitos, tarea mínima reversible, pruebas concretas y protocolo de acciones. Antes de iniciarlo se auditan workflows y permisos para que el commit no active despliegue/trading involuntario. Si el CI de `feature/GRU` tiene efectos de producción, usar primero repo/rama/entorno de aceptación expresamente configurado; mantener un último gate real del target bajo su autorización operacional, sin fingir que el sandbox lo reemplaza.

Pasos requeridos:

1. Bootstrap nuevo en proyecto correcto; adjuntar el plan; un solo delivery probado.
2. Chat solicita probe local con nonce y target explícito; materializar/ejecutar/devolver stdout/stderr literal.
3. Chat solicita probe VPS read-only con otro nonce; verificar host/receipt y devolver evidencia.
4. Chat solicita lectura GitHub read-only del repo/ref esperado; evidencia correlacionada.
5. Escritor autorizado implementa el cambio mínimo y publica un commit consolidado de esa iteración; operator solo observa.
6. Controller identifica candidato, espera CI/Semaphore exactos, entrega resultado y solicita revisión final.
7. Chat produce GO explícito; verificador confirma todas las condiciones y genera evidencia por run.

### 10.2 Plan canary de recuperación

Destino **aislado** de producción con las mismas interfaces del controller y CI. INT define una validación acotada en el espacio de aceptación que falla de forma determinista por una condición corregible en código; el manifiesto registra la causa esperada y bloquea deploys del ensayo. No falsificar respuestas del adapter live ni editar estados para simular un failure.

1. Primera iteración publica su único commit y ejecuta un job que realmente falla.
2. Controller obtiene identity + logs exactos y reproducción aislada cuando es pertinente.
3. Devuelve evidencia al mismo chat, obtiene diagnóstico y solicita replan usando instrucciones reales de la skill.
4. Chat produce `.md` descargable; broker valida bytes/hash/contenido y persiste handoff.
5. Segunda iteración abre chat nuevo, adjunta ese archivo, implementa reparación y publica su único commit.
6. CI real pasa; revisión final y GO validados. Contar dos commits de dos iteraciones como comportamiento esperado, no duplicación.
7. Retirar el ensayo según política del entorno de aceptación y registrar limpieza; no reescribir historial ni borrar evidencia.

### 10.3 Reinicios live acotados

En T41 usar puntos de inyección controlados por QA, desactivados en la configuración operacional. Afectar únicamente PID/grupo del run de aceptación. No usar un `kill-all` global que derribe otras sesiones.

- Ensayo A: caída después del Send pero antes de marcar SENT. Resume observa el marcador y continúa sin otro click.
- Ensayo B: caída tras finalizar probe read-only antes de consolidar resultado en el controller. Resume consulta receipt y entrega una sola evidencia; si se decide reejecutar por ser read-only, la política debe registrarlo, pero no debe contar ese caso como prueba de ejecución única. El gate de receipt exige reutilizar el resultado original.

Las ventanas de acciones no idempotentes se cubren además con fixtures transaccionales y contador de efectos; no ejecutar una operación de trading real para probar at-most-once.

### 10.4 Condición de no intervención

Desde el primer Send hasta GO, los canaries requieren **cero** mensajes `continúa/procede` escritos por el humano, cero correcciones manuales de state/ledger/CI, cero commits del operator y cero selecciones manuales de modelo para superar bugs. Login/2FA legítimo se resuelve antes del ensayo; si aparece a mitad, se conserva el run y se reporta bloqueado. La corrida completa se repite después de resolver la dependencia para obtener evidencia de autonomía; el bloqueo anterior no cuenta como PASS.

## 11. Pre-mortem deliberado: tres fallos posibles

| Escenario | Señal temprana | Prevención / detección | Recuperación y dueño |
|---|---|---|---|
| 1. “Arreglamos el selector”, pero elegimos Light/Work o aprobamos texto del historial | PASS sin estado activo; múltiples matches; menú incompleto | Policy strict, pruebas negativas T03–T09 y revalidación previa a Send | Congelar envío, capturar DOM y corregir adapter; BR/FSM. |
| 2. Un restart duplica prompt, comando, commit o evidencia | Ledger SENDING/RUNNING sin receipt; IDs cambian tras resume | Intención durable, bindings, receipts, T13–T16/T32/T41 | Reconciliar; efecto desconocido bloquea; jamás retry ciego; FSM. |
| 3. Todo parece verde, pero el ciclo no puede terminar o el GO usa otro candidato | Chat sin writer, `.md` no descargable, CI empty/stale, deploy pendiente | Capabilities tempranas, T20/T23–T31, canaries reales y verificador independiente | Reparar integración o declarar dependencia exacta; nuevo gate desde checkpoint; INT/TL/QA. |

Tradeoff deliberado: controles más estrictos pueden bloquear ante UI parcialmente observada. La solución es mejorar observabilidad y recuperación acotada, no aceptar identidad desconocida. Ningún gate permite reducir seguridad para aumentar la tasa aparente de éxito.

## 12. Observabilidad y paquete de evidencia

Todo evento registra `run_id`, iteración, fase/subfase, delivery/action/request ID si corresponde, timestamp UTC, versión/release hash, policy hash y enlace a evidencia. El log de usuario debe decir causa, intento/presupuesto, próxima acción y cómo reanudar. Registrar latencia de bootstrap, política, respuesta, acción, CI y recovery; contadores de reconciliación, rate limit, bloqueo y GO rechazado.

Eventos mínimos nuevos o normalizados: `MODEL_CATALOG_OBSERVED`, `POLICY_SELECTION_CONFIRMED`, `POLICY_GUARD_REJECTED`, `BOOTSTRAP_BLOCKED`, `DELIVERY_RECONCILED`, `ACTION_RESULT_UNKNOWN`, `CI_IDENTITY_MISMATCH`, `PLAN_HANDOFF_VERIFIED`, `GO_REJECTED`, `FULL_LOOP_ACCEPTED`.

Un `acceptance-manifest.json` enlazará:

- source commit/tree y manifest SHA de release; hashes de binarios/config efectiva instalada;
- test ID, comando exacto, exit code, start/end, seed cuando aplique, versión de dependencias y paths/hashes de resultados;
- run/iteración, proyecto/chat, policy proof y todos los delivery/action receipts;
- repo/rama/baseline/candidate, provider/run/pipeline/attempt/job y logs CI;
- hash/origen de diagnóstico/plan de recuperación descargado y relaciones entre chats;
- verificación operacional si corresponde; `go_confirmed` por run y respuesta final asociada;
- resumen de pendientes, skips, fallos iniciales, cambios correctivos y conclusión independiente.

Evitar autorreferencia: T43 primero prueba el verificador con manifests de ensayo completos y adulterados, produciendo resultados de test separados. Congelar después el manifest de aceptación que referencia esos resultados. El verificador final lee ese manifest inmutable y escribe un archivo de veredicto separado con el hash del manifest. Un índice exterior del bundle puede referenciar ambos; ningún archivo necesita contener su propio hash ni el de un resultado que todavía no existe.

Mantener originales privados con permisos adecuados y redactar secretos en el bundle compartible. Los resultados textuales deben ser fieles; una redacción se marca y conserva su correlación con el hash del original privado. Nunca enviar a Chat un credential dump para “demostrar auth”.

## 13. Instalación, rollout y rollback

1. REL identifica el proceso dueño y coordina parada del run concreto; toma backup de runtime/config/state y manifest. No borrar el perfil autenticado ni `/tmp/log`.
2. Preparar bundle v4.3 en staging. Mantener nombres legacy de daemon/CLI; nuevos scripts/versiones se anuncian solo cuando existen y pasan tests.
3. Verificar sintaxis Python/Node y pruebas offline **del mismo bundle**. No sustituir dependencias a ciegas por “latest”; fijar versiones compatibles observadas.
4. Instalar grupo coherente de controller/broker/worker/prompts/policy/config mediante estrategia atómica o rollback probado. No sobrescribir config de usuario ni secretos.
5. Migrar copia de state, validar, hacer checkpoint y activar con schema compatible. Bloquear downgrade que no entienda el state nuevo. Reanudar no requiere borrar ledgers.
6. Comparar hashes instalados, ejecutar doctor y G2–G5. El reporte local verde solo significa `OFFLINE_PASS`, no release aceptada.
7. Si falla instalación/compatibilidad: detener solo procesos propios, restablecer bundle/config compatibles y conservar evidencia/estado. Un rollback después de efectos nuevos debe reconciliar esos efectos antes de usar estado antiguo; restaurar un backup viejo del ledger a ciegas puede duplicarlos.

Consolidar cambios del control plane en su repo/rama determinada por B01; los especialistas entregan diffs, TL integra y hace el commit de release cuando corresponda a la ejecución autorizada. El commit del control plane, los commits canary y los del target son objetos distintos en el manifest.

**Si aparece cualquier cambio de código después de G1**, invalidar los resultados afectados mediante análisis explícito de dependencias y repetir los gates necesarios; si cambia controller/broker/transporte/CI/GO, volver a ejecutar los canaries afectados. No declarar aceptación de un bundle distinto al ensayado.

## 14. Runbook concreto de implementación y recuperación

### 14.1 Primeros pasos del equipo

En el host del usuario, como acciones de inspección autorizadas dentro de la implementación:

```bash
cd /mnt/d/works/ai-control-plane
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
rg --files -g AGENTS.md -g '*broker*' -g '*loopd*' -g '*selftest*' -g '*preflight*'
rg -n 'MODEL_SOL_OPTION_NOT_FOUND|ENSURE_CHAT_POLICY|start_new_chat|SEND_ATOMIC' ai-loop-v4.2
```

Leer instrucciones de repositorio y evidencia indicada en §2.3. No interpretar un `rg` sin resultados como permiso para reconstruir todo el producto; localizar versión instalada y diferencias.

Los comandos siguientes están **documentados como existentes en v4.2**, pero el equipo verifica existencia/versión antes de usarlos:

```bash
cd /mnt/d/works/ai-control-plane/ai-loop-v4.2
./bin/verify-v4.2-local
/opt/ai-loop/bin/status-loop-v3
```

No ejecutar `install.sh` mientras exista un owner activo sin parada/checkpoint coordinados. Los binarios de aceptación propuestos abajo todavía deben implementarse en B14/B40; no se presentan como disponibles ahora.

### 14.2 Interfaz de verificación a entregar

REL/TL definirán y documentarán una CLI real equivalente al siguiente contrato. Los nombres son **propuestos para v4.3**, no comandos verificados de v4.2:

```text
bin/verify-v4.3-local
bin/doctor-chat-policy-v4.3 --project-config <config> --no-send --output <dir>
bin/preflight-v4.3 --plan <plan.md> --manifest <acceptance-config.json>
bin/acceptance-v4.3 --scenario happy|recovery|restart|target --manifest <config>
bin/verify-acceptance-v4.3 --manifest <acceptance-manifest.json>
```

Contrato: rc=0 solo si se satisfacen todos los requisitos del modo; rc no cero y resultado estructurado para fallo/bloqueo. No permitir `--skip-required`, `--force-go` o equivalente. Modo no-send nunca delega a un runner que pueda enviar. Configurar el entorno/scenario en manifest, no en comandos shell construidos desde salida no confiable.

### 14.3 Recuperar el run original después del fix

Revisar state + delivery ledger + DOM de `R20260922T024027` antes de tomar una decisión. Si no existe state consistente, no fabricarlo: usar recuperación documentada con evidencia conservada y marcar el run fallido.

- Si no hubo Send ni efecto ambiguo: reanudar mismo state tras migración validada y reconstruir draft seguro.
- Si hubo Send confirmado o posiblemente realizado: enlazar chat correcto y reconciliar; nunca abrir otro chat para el mismo delivery a ciegas.
- Si el usuario quiere un objetivo nuevo, usar `start` con un nuevo plan; no reinterpretar `restart` como start.

Comandos existentes documentados para un state confirmado, solo tras verificar esos requisitos:

```bash
/opt/ai-loop/bin/restart-loop-v3 /var/lib/ai-loop/state/R20260922T024027.v3.json
tail -F /var/lib/ai-loop/logs/R20260922T024027.v3.log
```

La evidencia de ese run puede servir para T42 si realmente ejecuta el plan objetivo y cumple todos los requisitos; no contar dos veces el mismo ensayo como recuperación CI intencional.

## 15. Handoff de ejecución: team → ralph

La planificación termina con este archivo. **No se está invocando `/team` ni `/ralph` en el host del usuario desde esta sesión.** La skill adjunta describe planificación; la instalación local puede o no tener esos comandos. Verificarlos y, si no están, ejecutar el mismo reparto mediante `task(subagent_type="general", ...)`/`explore` y coordinador local. No instalar plugins o inventar agentes para aparentar cumplimiento.

### 15.1 Lanzamiento sugerido de team

Usar este contenido como prompt en el checkout del **control plane**, adjuntando este archivo. La sintaxis del prefijo `/team` o `team` se adapta a la instalación; no se asume un CLI `--agents` inexistente:

```text
/team Implementa completamente el plan adjunto de ai-loop v4.3.
Equipo total: 6 (TL coordinador, BR browser, FSM estado/transporte,
INT integraciones, QA verificación independiente, REL release).
Trabaja en /mnt/d/works/ai-control-plane; verifica repo/rama/HEAD/AGENTS
antes de editar. Trochez/bot_trading:feature/GRU es el target del loop,
no el repositorio donde insertar esta reparación del control plane.
Ejecuta B01-B49 por dependencias, conserva cambios ajenos, y asigna
propietario único por archivo. Usa general/explore disponibles; no fijes
modelos de agentes ni modifiques el modelo/proveedor existente de OpenCode.
No cierres con selftests: completa G0-G5 y los canaries live hasta GO.
No cambies Chat por Work ni otorgues commit/push al operator.
Entrega manifest y evidencia verificable; si hay bloqueo externo real,
decláralo concretamente sin presentarlo como éxito.
```

### 15.2 Paso de team a ralph y camino secuencial

Team entrega a QA/TL: revisión congelada, manifest de bundle, resultados, candidatos/CI y backlog sin tareas críticas abiertas. Después se ejecuta una fase **secuencial** de verificación tipo ralph. QA dirige; consulta `general` para auditoría independiente y `explore` para localizar evidencia, sin un segundo browser owner.

```text
/ralph Verifica y cierra el plan adjunto sobre la revisión congelada y
el acceptance-manifest entregado por team. Reproduce los gates faltantes
o invalidados, audita los canaries live y comprueba SHA/CI/GO/receipts.
No aceptes skips obligatorios, artefactos simulados o simples afirmaciones.
Si detectas defecto, devuelve su Bxx/Txx al propietario, exige corrección
y repite los gates afectados sobre el nuevo bundle. Finaliza únicamente
con FULL_LOOP_ACCEPTED demostrado o bloqueo externo explícito con checkpoint.
```

Alternativa sin team: un coordinador implementa carriles secuencialmente, con revisiones `general` por separado y el mismo QA final. No suprimir la independencia ni las pruebas por reducir concurrencia. Razonamiento alto para arquitectura/browser/FSM/CI y revisión; medio/alto para empaquetado; ajustar al proveedor ya configurado sin imponer otro modelo.

Si revisores no están disponibles, registrar la indisponibilidad y revisión local sustitutiva conforme a la skill; nunca inventar consenso externo. Budgets de revisión usan `OMX_CONSENSUS_AGENT_TIMEOUT_MS`, `OMX_CONSENSUS_TOTAL_TIMEOUT_MS`, `OMX_CONSENSUS_MAX_REVIEW_ITERATIONS` y el circuit breaker documentado; no sleeps fijos. No confundir el presupuesto de planificación con los deadlines del runtime.

## 16. Criterios finales de aceptación y reporte obligatorio

- [ ] D01/D02 explicados y causas de bootstrap probadas con evidencia; hipótesis restantes identificadas.
- [ ] Política efectiva y UI seleccionada coinciden; ninguna degradación silenciosa ni Work/Codex.
- [ ] Fuente/runtime/config y todos los resultados pertenecen al bundle aceptado.
- [ ] G0–G5 completados; T01–T43 y regresiones obligatorias con evidencia, sin skips encubiertos.
- [ ] Happy path y recuperación CI live completos; OpenCode/local/GitHub/VPS/Semaphore/artefactos ejercitados.
- [ ] Writer en Chat demostrado; operator nunca hizo commit/push.
- [ ] Cero envíos a proyecto incorrecto, cero efectos duplicados, cero retries ciegos y cero GO falsos.
- [ ] Reinicio conserva run/chat/ledger y termina; lock/cleanup no afectan otros procesos.
- [ ] Plan real descargado durante recovery, nuevo chat y nueva iteración vinculados por hashes.
- [ ] HEAD remoto = candidato, CI requerido y vigente verde, deploy verificado si aplica, GO posterior válido.
- [ ] No hay acciones/deliveries ambiguos, failure stages abiertos ni defectos P0/P1.
- [ ] QA verifica manifest de manera independiente y emite `FULL_LOOP_ACCEPTED`.

Entregables de implementación: código/tests, bundle instalable, `IMPLEMENTATION_REPORT_<datetime>.md`, `KNOWN_LOG_FINDINGS_COVERAGE.md` actualizado, matriz Bxx/Txx/evidencia, manifests de release/aceptación, canaries `.md`, runbook/rollback y pruebas `go_confirmed` por run. Cada fallo encontrado durante implementación entra al backlog con dueño/test; no ocultarlo porque no apareció en el traceback inicial.

Reporte de cierre debe indicar: qué cambió; causa demostrada; repo/branch/SHA de control plane y target; suites y escenarios ejecutados; evidencia y restricciones; resultado **ACCEPTED**, **NO_GO_INTERNAL** o **BLOCKED_EXTERNAL**. Un bloqueo describe quién/dependencia, acción mínima necesaria, datos no secretos que lo prueban y comando/checkpoint para continuar. No equivale a objetivo cumplido.

## 17. Registro de consenso de esta planificación

Planner: hilo principal. Contexto previo creado en `.omx/context/ai-loop-model-policy-full-loop-20260922T080906Z.md`. Se aplicó deliberación por incidente de bootstrap y efectos sobre Git/CI/VPS.

Revisión Arquitecto, ronda 1: **APPROVE**, realizada por un revisor independiente mediante colaboración disponible. Antítesis más fuerte: parche mínimo del selector más canary temprano, para evitar reimplementar garantías que podrían existir. Tensión: la verificación estricta reduce falsos GO a costa de bloquear cuando la observación es parcial. Síntesis incorporada: tareas `VERIFIED_EXISTING`, estados de capacidad separados, cierre de manifest sin autorreferencia y GO como observación fechada. No se identificaron violaciones de principios ni bloqueos arquitectónicos.

Revisión Crítico, ronda 1: **APPROVE**, realizada después de concluir Arquitectura e incorporar sus observaciones. Confirmó consistencia de principios/opciones, límites del diagnóstico, seis roles/backlog, pruebas deliberadas y ausencia de rutas de falso éxito. Se incorporaron sus dos mejoras menores: B12 depende explícitamente de B04; T35/T43 validan campos de observabilidad y vínculos evento→evidencia. No se requirió una ronda ITERATE/REJECT.

Consenso final: **Planner → Architect APPROVE → Critic APPROVE**, en orden secuencial. Revisión de agentes real mediante el mecanismo disponible; no se simuló `task()` de OpenCode. Aprobación del plan no significa aprobación de una implementación ni PASS live. El riesgo residual decisivo sigue siendo la disponibilidad real del par modelo/reasoning y del writer autorizado en Chat, que deberán probarse en ejecución.

## 18. Referencias técnicas y procedencia

- [D1] Documento adjunto `DOCUMENTACION_COMPLETA_AI_LOOP_V4_2_20260922T0155-0500.md`; fuente del comportamiento/invariantes v4.2, no una inspección independiente de su implementación.
- [D2] Traceback del usuario del run `R20260922T024027`; fuente del punto exacto de fallo observado.
- [D3] Skill adjunta `SKILL(4).md`, nombre `omo-ralplan`; fuente del procedimiento deliberativo.
- [S1] [Playwright — Locators](https://playwright.dev/docs/locators), consultado 2026-09-22: localizadores por rol/nombre y alcance de controles. La aplicación a ChatGPT es decisión de diseño que requiere DOM real.
- [S2] [Playwright — Auto-waiting](https://playwright.dev/docs/actionability), consultado 2026-09-22: comprobaciones de accionabilidad y espera por condiciones. No prueban que una política del producto haya quedado seleccionada.
- [S3] [GitHub REST — Check runs](https://docs.github.com/en/rest/checks/runs), consultado 2026-09-22: consulta de checks por ref/SHA. La lista de checks obligatorios y la correlación Semaphore pertenecen al contrato del proyecto, no se infieren de esa página.

No se ha verificado por una página pública qué modelos existen hoy en la cuenta del usuario. El catálogo permitido y observado se obtiene de su sesión real y su configuración autorizada durante B03/B06/B09.
