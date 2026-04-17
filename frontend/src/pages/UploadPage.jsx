import { useRef, useState } from 'react'
import api from '../services/api'

export default function UploadPage() {
  const [status, setStatus] = useState('')
  const [records, setRecords] = useState([])
  const [dragActive, setDragActive] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const inputRef = useRef(null)

  const processFile = async (file) => {
    setIsProcessing(true)
    const form = new FormData()
    form.append('file', file)

    try {
      setStatus('Uploading...')
      const uploadResp = await api.post('/upload', form, { headers: { 'Content-Type': 'multipart/form-data' } })

      setStatus('Parsing file...')
      const parseResp = await api.post('/parse', { filename: uploadResp.data.filename })

      if (file.name.toLowerCase().endsWith('.csv')) {
        setStatus('Ingesting supplier graph to PostgreSQL...')
        await api.post('/ingest/supplier-csv', { filename: uploadResp.data.filename })
      }

      setRecords(parseResp.data.records || [])
      setStatus(`Parsed ${parseResp.data.count} records from ${parseResp.data.source_type.toUpperCase()} file`)
    } catch (error) {
      const message =
        error?.response?.data?.error ||
        error?.message ||
        'Upload failed. Please verify backend is running and try again.'
      setStatus(`Error: ${message}`)
    } finally {
      setIsProcessing(false)
    }
  }

  const onFileSelect = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    await processFile(file)
    event.target.value = ''
  }

  const onDrop = async (event) => {
    event.preventDefault()
    if (isProcessing) return
    setDragActive(false)
    const file = event.dataTransfer.files?.[0]
    if (!file) return
    await processFile(file)
  }

  return (
    <div className="space-y-6">
      <h2 className="font-display text-3xl tracking-tight">Upload & Parse Business Files</h2>

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragActive(true)
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => !isProcessing && inputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed p-10 text-center transition ${
          dragActive ? 'border-cyan-500 bg-cyan-50' : 'border-slate-300 bg-white'
        }`}
      >
        <p className="font-medium text-slate-700">Drag & drop Excel/PDF files here</p>
        <p className="mt-2 text-sm text-slate-500">
          {isProcessing ? 'Please wait, processing file...' : 'or click to browse'}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.csv,.pdf"
          onChange={onFileSelect}
          className="hidden"
          disabled={isProcessing}
        />
      </div>

      {status && <p className="rounded-xl bg-slate-100 p-3 text-slate-700">{status}</p>}

      <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-4 py-3">Supplier</th>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Delay</th>
              <th className="px-4 py-3">Issue</th>
            </tr>
          </thead>
          <tbody>
            {records.map((row, idx) => (
              <tr key={idx} className="border-t border-slate-100">
                <td className="px-4 py-3">{row.supplier || 'unknown'}</td>
                <td className="px-4 py-3">{row.product || 'unknown'}</td>
                <td className="px-4 py-3">{row.delay ?? row.delay_days ?? 0}</td>
                <td className="px-4 py-3">{row.issue || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
