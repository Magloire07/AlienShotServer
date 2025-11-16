<script setup>
import { onMounted, ref, watch } from 'vue'
import PhotoGrid from '../components/PhotoGrid.vue'
import api, { shareFileUrl } from '../services/api'

const props = defineProps({
  token: { type: String, required: true }
})

const photos = ref([])
const selectedIds = ref([])
const loading = ref(true)
const errorMessage = ref('')
const shareDate = ref('')

const fetchShare = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await api.get(`/shares/${props.token}`)
    photos.value = response.data.photos
    shareDate.value = response.data.created_at
    selectedIds.value = []
  } catch (error) {
    errorMessage.value = error.response?.data || 'Partage introuvable.'
  } finally {
    loading.value = false
  }
}

const toggleSelection = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((value) => value !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

const buildPhotoSrc = (photo) => shareFileUrl(props.token, photo.id)

const downloadPhotos = async (photoIds = []) => {
  if (!photos.value.length) return
  try {
    const response = await api.post(
      `/shares/${props.token}/download`,
      photoIds.length ? { photo_ids: photoIds } : {},
      { responseType: 'blob' }
    )
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `alienshot-${props.token}.zip`
    anchor.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error.response?.data || 'Téléchargement impossible.'
  }
}

const downloadSelected = () => {
  if (!selectedIds.value.length) return
  downloadPhotos(selectedIds.value)
}

const downloadAll = () => downloadPhotos([])

onMounted(fetchShare)

watch(
  () => props.token,
  () => {
    fetchShare()
  }
)
</script>

<template>
  <section class="panel">
    <h1>Sélection partagée</h1>
    <p v-if="shareDate">Créée le {{ new Date(shareDate).toLocaleString('fr-FR') }}</p>

    <p v-if="loading">Chargement en cours...</p>
    <p v-if="errorMessage" class="status error">{{ errorMessage }}</p>

    <PhotoGrid
      v-if="!loading && !errorMessage"
      :photos="photos"
      :selected-ids="selectedIds"
      :get-photo-src="buildPhotoSrc"
      :link-builder="buildPhotoSrc"
      @toggle="toggleSelection"
    />

    <div v-if="photos.length" class="toolbar" style="margin-top: 1.5rem">
      <button class="secondary" :disabled="!selectedIds.length" @click="downloadSelected">
        Télécharger sélection
      </button>
      <button @click="downloadAll">Tout télécharger</button>
    </div>
    <p v-if="photos.length" class="muted">Cliquez sur les images pour les prévisualiser puis choisissez ce que vous souhaitez récupérer.</p>
  </section>
</template>
