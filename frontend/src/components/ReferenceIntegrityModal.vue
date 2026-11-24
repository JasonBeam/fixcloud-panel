<script setup lang="ts">
import { AlertTriangle, ArrowRightLeft, Link2, Trash2, X } from "lucide-vue-next";

import { referenceGuardState, resolveReferenceDelete } from "@/composables/referenceGuard";
</script>

<template>
  <Teleport to="body">
    <div v-if="referenceGuardState.open && referenceGuardState.impact" class="modal-layer" role="dialog" aria-modal="true" aria-label="删除引用完整性检查">
      <section class="app-dialog-card reference-impact-dialog">
        <header class="picker-header">
          <div>
            <p class="eyebrow">删除前检查</p>
            <h2>“{{ referenceGuardState.impact.name }}”</h2>
            <p class="reference-impact-type">{{ referenceGuardState.impact.type }} · 已扫描当前草稿完整结构</p>
          </div>
          <button class="icon-button" aria-label="取消删除" @click="resolveReferenceDelete('cancel')"><X :size="19" /></button>
        </header>

        <div class="reference-impact-body">
          <section v-if="referenceGuardState.impact.references.length" class="reference-impact-section">
            <h3><Link2 :size="16" />直接引用 {{ referenceGuardState.impact.references.length }} 处</h3>
            <ul>
              <li v-for="item in referenceGuardState.impact.references" :key="JSON.stringify(item.path)">
                <strong>{{ item.relation }}</strong><span>{{ item.label }}</span>
              </li>
            </ul>
          </section>
          <section v-if="referenceGuardState.impact.chains.length" class="reference-impact-section">
            <h3><ArrowRightLeft :size="16" />嵌套影响链</h3>
            <ul><li v-for="item in referenceGuardState.impact.chains" :key="item">{{ item }}</li></ul>
          </section>
          <section v-if="referenceGuardState.impact.warnings.length" class="reference-impact-warning">
            <AlertTriangle :size="17" />
            <div><strong>可能导致无效或不符合预期的配置</strong><p v-for="item in referenceGuardState.impact.warnings" :key="item">{{ item }}</p></div>
          </section>
          <p v-if="!referenceGuardState.impact.references.length && !referenceGuardState.impact.chains.length" class="reference-impact-empty">
            未找到明确引用；动态 include-all 或正则筛选关系仍需要你在 Diff 前确认。
          </p>
        </div>

        <footer class="reference-impact-actions">
          <button class="soft-button" @click="resolveReferenceDelete('cancel')">取消</button>
          <button v-if="referenceGuardState.impact.references.length" class="soft-button" @click="resolveReferenceDelete('remove')">
            同时移除相关引用
          </button>
          <div v-if="referenceGuardState.impact.references.length && referenceGuardState.impact.replacementOptions.length" class="reference-replace-control">
            <select v-model="referenceGuardState.replacement" aria-label="替代对象">
              <option v-for="option in referenceGuardState.impact.replacementOptions" :key="option" :value="option">{{ option }}</option>
            </select>
            <button class="primary-button" @click="resolveReferenceDelete('replace')">批量替换</button>
          </div>
          <button class="danger-button" @click="resolveReferenceDelete('keep')"><Trash2 :size="16" />仅删除当前项</button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>
.reference-impact-dialog { width: min(700px, 100%); max-height: min(760px, calc(100dvh - 40px)); overflow: auto; }
.reference-impact-type { margin: 5px 0 0; color: var(--text-muted); font-size: 12px; }
.reference-impact-body { display: grid; gap: 12px; padding: 4px 0 18px; }
.reference-impact-section { overflow: hidden; border: 1px solid var(--separator); border-radius: 14px; background: var(--field-bg); }
.reference-impact-section h3 { display: flex; align-items: center; gap: 7px; margin: 0; padding: 11px 13px; border-bottom: 1px solid var(--separator); color: var(--text-primary); font-size: 13px; }
.reference-impact-section ul { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.reference-impact-section li { display: grid; gap: 2px; padding: 9px 13px; border-bottom: 1px solid var(--separator); font-size: 12px; }.reference-impact-section li:last-child { border-bottom: 0; }.reference-impact-section li span { color: var(--text-muted); }
.reference-impact-warning { display: flex; gap: 10px; border: 1px solid rgba(245, 158, 11, .35); border-radius: 14px; padding: 12px; color: #a16207; background: rgba(245, 158, 11, .1); font-size: 12px; }.dark .reference-impact-warning { color: #fbbf24; }.reference-impact-warning p { margin: 4px 0 0; line-height: 1.55; }.reference-impact-empty { margin: 0; color: var(--text-muted); font-size: 13px; line-height: 1.6; }
.reference-impact-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }.reference-replace-control { display: flex; min-width: 230px; flex: 1; gap: 7px; }.reference-replace-control select { min-width: 0; flex: 1; border: 1px solid var(--separator); border-radius: 10px; padding: 0 9px; color: var(--text-primary); background: var(--field-bg); }
@media (max-width: 640px) { .reference-impact-actions, .reference-replace-control { width: 100%; }.reference-impact-actions > button { flex: 1; justify-content: center; } }
</style>
