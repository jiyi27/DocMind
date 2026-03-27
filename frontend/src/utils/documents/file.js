import { Document, Memo } from '@element-plus/icons-vue'

export function getFileExtension(fileName) {
  if (!fileName || !fileName.includes('.')) return ''
  return fileName.split('.').pop().toLowerCase()
}

export function getFileIcon(fileName) {
  const extension = getFileExtension(fileName)

  if (extension === 'md' || extension === 'markdown') {
    return Memo
  }

  return Document
}
