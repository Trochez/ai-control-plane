# Documentos requeridos para ejecutar el `/omo-team` actual

Run autoritativo: `R20260923T012014`

## Documentos que debes proporcionar a OpenCode

1. **Plan actual — obligatorio**
   - `IMPLEMENTATION_PLAN_AI_LOOP_V4_8_9_MODEL_POLICY_RECONCILIATION_AND_CONDITIONAL_DELIVERY_20260927.md`
   - Es el plan que se debe ejecutar ahora.

2. **Plan predecesor v4.8.8 — obligatorio como contrato autoritativo previo**
   - `IMPLEMENTATION_PLAN_AI_LOOP_V4_8_8_ARTIFACT_BOUND_SUCCESSOR_PREFLIGHT_DELIVERY_PROOF_WITH_MAIN_PUSH_20260926.md`
   - Define el proof package y el lease READY existentes, además de la reconciliación de la publicación Git.

3. **Skill `/omo-team` — obligatorio si no está instalado/cargado en OpenCode**
   - `OMO_TEAM_SKILL.md`
   - Es la definición de la skill `omo-team` usada para ejecutar el plan con subagentes coordinados.
   - Si `/omo-team` ya está instalado y reconocido por OpenCode, no necesitas copiarlo de nuevo; se incluye en el paquete para que el conjunto sea autocontenido.

## Evidencia runtime que debe existir en la máquina

No son documentos de reemplazo ni deben reconstruirse desde el ZIP. El plan espera encontrar la evidencia autoritativa ya existente en:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight/
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/
/var/lib/ai-loop/runs/R20260923T012014/control-plane-main-publication/
```

El lease existente debe continuar:

```text
PROOF_LEASE=READY
PROOF_LEASE_CONSUMED=false
```

Y el payload autoritativo debe existir en:

```text
/var/lib/ai-loop/runs/R20260923T012014/two-successor-commits-preflight-delivery-proof-v488/payload.txt
```

## Planes históricos que NO necesitas para esta ejecución

Los planes v4.8.5, v4.8.6 y v4.8.7 fueron intentos bloqueados y ya están superseded por v4.8.8/v4.8.9. No son necesarios para ejecutar el paso actual.

## Comando recomendado

```text
/omo-team execute IMPLEMENTATION_PLAN_AI_LOOP_V4_8_9_MODEL_POLICY_RECONCILIATION_AND_CONDITIONAL_DELIVERY_20260927.md for authoritative run R20260923T012014.

Use IMPLEMENTATION_PLAN_AI_LOOP_V4_8_8_ARTIFACT_BOUND_SUCCESSOR_PREFLIGHT_DELIVERY_PROOF_WITH_MAIN_PUSH_20260926.md as the authoritative predecessor contract for the existing v4.8.8 proof package and READY lease.

Do not rerun the two-successor preflight or Git publication.
Do not create a new proof lease.
First reconcile the model policy exactly as specified in v4.8.9.
Only if MODEL_POLICY_PROOF becomes PASS or BOUND_PRIOR_PASS may the existing lease be consumed and the exactly-once delivery proceed.
Stop immediately after capturing and classifying the settled response.
```
