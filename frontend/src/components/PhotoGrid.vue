<script setup>
const props = defineProps({
  photos: { type: Array, required: true },
  selectedIds: { type: Array, default: () => [] },
  selectable: { type: Boolean, default: true },
  showEmpty: { type: Boolean, default: true },
  getPhotoSrc: { type: Function, required: true },
  linkBuilder: { type: Function, default: null }
})

const emit = defineEmits(['toggle'])

const isSelected = (id) => props.selectedIds.includes(id)

const formatDate = (value) => {
  if (!value) return 'Date inconnue'
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}
</script>

<template>
  <div v-if="!photos.length && showEmpty" class="empty-state">
    <p>Aucune photo disponible pour le moment.</p>
  </div>
  <div v-else class="photo-grid">
    <article v-for="photo in photos" :key="photo.id" class="photo-card">
      <label v-if="selectable" class="checkbox">
        <input
          type="checkbox"
          :checked="isSelected(photo.id)"
          @change="emit('toggle', photo.id)"
        />
        <span>{{ isSelected(photo.id) ? 'Choisie' : 'Choisir' }}</span>
      </label>
      <a v-if="linkBuilder" :href="linkBuilder(photo)" target="_blank" rel="noreferrer">
        <img :src="getPhotoSrc(photo)" :alt="photo.original_name" loading="lazy" />
      </a>
      <img
        v-else
        :src="getPhotoSrc(photo)"
        :alt="photo.original_name"
        loading="lazy"
      />
      <footer>
        <strong>{{ photo.original_name }}</strong>
        <span>{{ formatDate(photo.created_at) }}</span>
      </footer>
    </article>
  </div>
</template>
