<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.budgetLabel') }}</h3>
        </div>
        <div class="budget-slider-row">
          <input
            v-model.number="budget"
            type="range"
            min="0"
            max="25000"
            step="250"
            class="budget-slider"
          />
          <span class="budget-readout">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">{{ t('restocking.totalCost') }}</div>
            <div class="stat-value">{{ currencySymbol }}{{ recommendations.total_cost.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ t('restocking.remainingBudget') }}</div>
            <div class="stat-value">{{ currencySymbol }}{{ recommendations.remaining_budget.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ t('restocking.itemsSelected', { count: recommendations.items.length }) }}</div>
            <div class="stat-value">{{ recommendations.items.length }}</div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.title') }}</h3>
        </div>

        <div v-if="recommendations.items.length === 0" class="loading">
          <div>{{ t('restocking.noRecommendations') }}</div>
          <div class="hint">{{ t('restocking.increaseBudgetHint') }}</div>
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.category') }}</th>
                <th>{{ t('restocking.table.warehouse') }}</th>
                <th>{{ t('restocking.table.quantityOnHand') }}</th>
                <th>{{ t('restocking.table.reorderPoint') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.recommendedQuantity') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations.items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.category }}</td>
                <td>{{ item.warehouse }}</td>
                <td>{{ item.quantity_on_hand }}</td>
                <td>{{ item.reorder_point }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td><strong>{{ item.recommended_quantity }}</strong></td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toLocaleString() }}</td>
                <td>{{ currencySymbol }}{{ item.line_cost.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="place-order-row">
          <button
            class="place-order-btn"
            :disabled="recommendations.items.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
          <span v-if="submitMessage" :class="['submit-message', submitMessage.type]">
            {{ submitMessage.text }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitMessage = ref(null)

    const budget = ref(5000)
    const recommendations = ref({ budget: 0, total_cost: 0, remaining_budget: 0, items: [] })

    let debounceTimer = null

    const loadRecommendations = async () => {
      try {
        error.value = null
        recommendations.value = await api.getRestockRecommendations(budget.value)
      } catch (err) {
        error.value = 'Failed to load restock recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Debounce slider-driven reloads (many events fire while dragging) without
    // toggling the full-page loading state, so the table updates in place.
    watch(budget, () => {
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 150)
    })

    const placeOrder = async () => {
      submitting.value = true
      submitMessage.value = null
      try {
        const payload = {
          budget: budget.value,
          items: recommendations.value.items.map(item => ({
            sku: item.sku,
            item_name: item.item_name,
            quantity: item.recommended_quantity,
            unit_cost: item.unit_cost,
            line_cost: item.line_cost
          }))
        }
        await api.createRestockOrder(payload)
        submitMessage.value = { type: 'success', text: t('restocking.orderSuccess') }
        await loadRecommendations()
      } catch (err) {
        submitMessage.value = { type: 'error', text: t('restocking.orderError') }
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      currencySymbol,
      loading,
      error,
      submitting,
      submitMessage,
      budget,
      recommendations,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-slider-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.budget-slider {
  flex: 1;
  accent-color: #3b82f6;
  cursor: pointer;
}

.budget-slider:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.budget-readout {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 100px;
  text-align: right;
}

.hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
}

.place-order-row {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 1.25rem;
}

.place-order-btn {
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.938rem;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.submit-message {
  font-size: 0.875rem;
  font-weight: 600;
}

.submit-message.success {
  color: #16a34a;
}

.submit-message.error {
  color: #dc2626;
}
</style>
