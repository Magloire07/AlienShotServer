<script setup>
import { computed, onMounted, ref } from 'vue'
import QrcodeVue from 'qrcode.vue'
import PhotoGrid from '../components/PhotoGrid.vue'
import api, { adminHeaders, photoFileUrl } from '../services/api'

const passwordInput = ref('')
const adminPassword = ref(window.sessionStorage.getItem('alienshot-admin-password') || '')
const photos = ref([])
const selectedIds = ref([])
const statusMessage = ref('')
const errorMessage = ref('')
const shareDetails = ref(null)
const uploading = ref(false)
const deleting = ref(false)
const generating = ref(false)

const isUnlocked = computed(() => Boolean(adminPassword.value))
const selectionCount = computed(() => selectedIds.value.length)

const persistPassword = () => {
  if (adminPassword.value) {
    window.sessionStorage.setItem('alienshot-admin-password', adminPassword.value)
  }
}

const unlock = async () => {
  if (!passwordInput.value.trim()) {
    errorMessage.value = 'Merci de saisir le mot de passe admin.'
    return
  }
  adminPassword.value = passwordInput.value.trim()
  persistPassword()
  await fetchPhotos()
}

const fetchPhotos = async () => {
  if (!adminPassword.value) return
  try {
    const response = await api.get('/photos', { headers: adminHeaders(adminPassword.value) })
    photos.value = response.data
    selectedIds.value = []
    statusMessage.value = `Chargé (${photos.value.length} photos)`
    errorMessage.value = ''
  } catch (error) {
    handleError(error)
  }
}

const handleUpload = async (event) => {
  const files = Array.from(event.target.files || [])
  if (!files.length || !adminPassword.value) return
  uploading.value = true
  const data = new FormData()
  files.forEach((file) => data.append('photos', file))

  try {
    await api.post('/images/add', data, {
      headers: { ...adminHeaders(adminPassword.value), 'Content-Type': 'multipart/form-data' }
    })
    statusMessage.value = `${files.length} photo(s) importées`
    await fetchPhotos()
  } catch (error) {
    handleError(error)
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}

const toggleSelection = (id) => {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter((value) => value !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

const deleteSelected = async () => {
  if (!selectionCount.value) return
  deleting.value = true
  try {
    await api.delete('/photos', {
      headers: adminHeaders(adminPassword.value),
      data: { photo_ids: selectedIds.value }
    })
    statusMessage.value = 'Photos supprimées'
    shareDetails.value = null
    await fetchPhotos()
  } catch (error) {
    handleError(error)
  } finally {
    deleting.value = false
  }
}

const generateShare = async () => {
  if (!selectionCount.value) return
  generating.value = true
  try {
    const response = await api.post(
      '/shares',
      { photo_ids: selectedIds.value },
      { headers: adminHeaders(adminPassword.value) }
    )
    shareDetails.value = response.data
    statusMessage.value = 'Lien de partage créé'
  } catch (error) {
    handleError(error)
  } finally {
    generating.value = false
  }
}

const buildPhotoSrc = (photo) => {
  if (!adminPassword.value) return ''
  return photoFileUrl(photo.id, adminPassword.value)
}

const handleError = (error) => {
  if (error.response && error.response.status === 403) {
    errorMessage.value = 'Mot de passe invalide.'
    adminPassword.value = ''
    window.sessionStorage.removeItem('alienshot-admin-password')
  } else {
    errorMessage.value = error.response?.data ?? 'Erreur inattendue'
  }
}

onMounted(() => {
  if (adminPassword.value) {
    fetchPhotos()
  }
})
</script>

<template>
  <section class="panel">
    <h1>Console sécurisée</h1>
    <p>Mot de passe par défaut : <code>admin</code> (à changer en prod via la variable <code>ADMIN_PASSWORD</code>).</p>

    <div v-if="!isUnlocked" class="toolbar">
      <input
        type="password"
        placeholder="Mot de passe admin"
        v-model="passwordInput"
        @keyup.enter="unlock"
      />
      <button @click="unlock">Déverrouiller</button>
    </div>

    <div v-else class="toolbar">
      <label class="btn secondary">
        <input type="file" accept="image/*" multiple @change="handleUpload" hidden />
        {{ uploading ? 'Import...' : 'Importer des photos' }}
      </label>
      <button class="secondary" @click="fetchPhotos">Rafraîchir</button>
      <button :disabled="!selectionCount" @click="generateShare">
        {{ generating ? 'Création...' : 'Générer QR' }}
      </button>
      <button class="danger" :disabled="!selectionCount || deleting" @click="deleteSelected">
        {{ deleting ? 'Suppression...' : 'Supprimer' }}
      </button>
      <span>{{ selectionCount }} sélection(s)</span>
    </div>

    <p v-if="statusMessage" class="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="status error">{{ errorMessage }}</p>

    <PhotoGrid
      v-if="isUnlocked"
      :photos="photos"
      :selected-ids="selectedIds"
      :get-photo-src="buildPhotoSrc"
      @toggle="toggleSelection"
    />
  </section>

  <section v-if="shareDetails" class="panel share-card">
    <h2>Lien partagé</h2>
    <p>
      Token: <code>{{ shareDetails.token }}</code><br />
      URL: <a :href="shareDetails.share_url" target="_blank">{{ shareDetails.share_url }}</a>
    </p>
    <div class="qr-wrapper">
      <QrcodeVue :value="shareDetails.share_url" :size="200" background="white" />
      <div>
        <p>Scannez ou envoyez ce QR pour accéder à la galerie publique.</p>
        <p>{{ shareDetails.photos.length }} photo(s) dans ce partage.</p>
      </div>
    </div>
  </section>
</template>
